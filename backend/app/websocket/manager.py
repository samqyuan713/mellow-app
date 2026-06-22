"""
Mellow — WebSocket Connection Manager
Real-time chat delivery via WebSocket.
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Set
from uuid import UUID
import json
import logging

from app.database import get_db
from app.utils.security import decode_token

logger = logging.getLogger("mellow.websocket")

router = APIRouter()


class ConnectionManager:
    """
    Manages active WebSocket connections.
    Maps user_id → set of active WebSocket connections
    (a user can have multiple browser tabs open).
    """

    def __init__(self):
        # user_id (str) → set of WebSocket connections
        self.active: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active:
            self.active[user_id] = set()
        self.active[user_id].add(websocket)
        logger.info(f"WS connected: user={user_id} total={len(self.active[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active:
            self.active[user_id].discard(websocket)
            if not self.active[user_id]:
                del self.active[user_id]
        logger.info(f"WS disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, data: dict):
        """Send a message to all connections for a specific user."""
        if user_id in self.active:
            dead = set()
            for ws in self.active[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.add(ws)
            # Clean up dead connections
            self.active[user_id] -= dead

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active and len(self.active[user_id]) > 0

    @property
    def online_count(self) -> int:
        return len(self.active)


# Singleton manager — shared across all WebSocket connections
manager = ConnectionManager()


@router.websocket("/ws/chat/{match_id}")
async def websocket_chat(
    websocket: WebSocket,
    match_id: str,
    token: str,                         # passed as query param: ?token=xxx
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time chat.
    Connect: ws://mellow.app/ws/chat/{match_id}?token=<access_token>

    Message format (client → server):
    { "type": "message", "content": "Hello!" }

    Message format (server → client):
    { "type": "message", "match_id": "...", "sender_id": "...",
      "content": "Hello!", "created_at": "..." }
    """
    # Authenticate via token query param
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, user_id)

    try:
        # Announce online status
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "match_id": match_id,
            "online_count": manager.online_count
        })

        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content or len(content) > 1000:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Message content is required and must be under 1000 characters"
                    })
                    continue

                # Save message to DB via service
                from app.models.message import Message
                from app.models.profile import Profile
                from app.models.match import Match
                from sqlalchemy import select, or_, update
                from datetime import datetime

                # Get sender's profile
                profile_result = await db.execute(
                    select(Profile).where(Profile.user_id == UUID(user_id))
                )
                my_profile = profile_result.scalar_one_or_none()
                if not my_profile:
                    continue

                # Verify match access
                match_result = await db.execute(
                    select(Match).where(
                        Match.id == UUID(match_id),
                        Match.is_active == True,
                        or_(
                            Match.profile_1_id == my_profile.id,
                            Match.profile_2_id == my_profile.id
                        )
                    )
                )
                match = match_result.scalar_one_or_none()
                if not match:
                    await websocket.send_json({"type": "error", "message": "Match not found"})
                    continue

                # Save message
                message = Message(
                    match_id=UUID(match_id),
                    sender_id=my_profile.id,
                    content=content,
                )
                db.add(message)
                match.last_message_at = datetime.utcnow()
                await db.commit()
                await db.refresh(message)

                # Broadcast to both users
                msg_payload = {
                    "type":       "message",
                    "id":         str(message.id),
                    "match_id":   match_id,
                    "sender_id":  str(my_profile.id),
                    "content":    message.content,
                    "created_at": message.created_at.isoformat(),
                    "is_read":    False,
                }

                # Send to sender (confirmation)
                await websocket.send_json({**msg_payload, "is_mine": True})

                # Send to recipient
                other_id = str(match.other_profile_id(my_profile.id))
                # Get other user's user_id
                other_profile_result = await db.execute(
                    select(Profile).where(Profile.id == UUID(other_id))
                )
                other_profile = other_profile_result.scalar_one_or_none()
                if other_profile:
                    await manager.send_to_user(
                        str(other_profile.user_id),
                        {**msg_payload, "is_mine": False}
                    )

            elif msg_type == "typing":
                # Broadcast typing indicator to the other user
                await websocket.send_json({
                    "type":     "typing",
                    "match_id": match_id,
                    "user_id":  user_id,
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
