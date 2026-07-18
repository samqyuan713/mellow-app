"""
Mellow — Matches, Messages, Subscriptions & Safety Routers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
from datetime import datetime, date
import logging

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile, Photo
from app.models.match import Match, Swipe, DailyLimit
from app.models.message import Message
from app.models.subscription import Subscription, Report, Block
from app.schemas.match import (
    SwipeRequest, SwipeResponse,
    MatchResponse, MatchedProfileSnippet,
    SendMessageRequest, MessageResponse, ConversationResponse,
    ReportRequest, BlockRequest, SafetyResponse,
    CheckoutSessionResponse, CustomerPortalResponse,
    SubscriptionResponse, PlanResponse, PlanFeatures,
)
from app.middleware.auth_middleware import (
    get_current_user, get_current_verified_user,
    get_current_subscription, require_premium
)
from app.config import settings

logger = logging.getLogger("mellow")


# ══════════════════════════════════════════
# MATCHES ROUTER
# ══════════════════════════════════════════
matches_router = APIRouter()


@matches_router.post("/swipe", response_model=SwipeResponse)
async def swipe_profile(
    data: SwipeRequest,
    current_user: User = Depends(get_current_verified_user),
    subscription: Subscription = Depends(get_current_subscription),
    db: AsyncSession = Depends(get_db)
):
    """Swipe like, pass or superlike on a profile."""
    # Get current user's profile
    my_result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    my_profile = my_result.scalar_one_or_none()
    if not my_profile:
        raise HTTPException(status_code=400, detail="Complete your profile first")

    # Check & enforce daily swipe limit for free users
    if not subscription.is_premium:
        limit_result = await db.execute(
            select(DailyLimit).where(
                DailyLimit.user_id == current_user.id,
                DailyLimit.date == date.today()
            )
        )
        daily = limit_result.scalar_one_or_none()

    # Create new daily limit record if doesn't exist
    if not daily:
        daily = DailyLimit(
            user_id=current_user.id,
            swipes_used=0,
            messages_sent=0,
            superlikes_used=0
        )
        db.add(daily)
        await db.flush()  # get the record into session

    # Ensure swipes_used is never None
    if daily.swipes_used is None:
        daily.swipes_used = 0

    # Check limit
    if daily.swipes_used >= settings.FREE_DAILY_SWIPES:
        raise HTTPException(
            status_code=402,
            detail=f"You've used your {settings.FREE_DAILY_SWIPES} free swipes today. Upgrade to Mellow Premium for unlimited swiping!"
        )

    # Increment counter
    daily.swipes_used += 1
    
    # Record the swipe
    existing = await db.execute(
        select(Swipe).where(
            Swipe.swiper_id == my_profile.id,
            Swipe.swiped_id == data.profile_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already swiped on this profile")

    swipe = Swipe(
        swiper_id=my_profile.id,
        swiped_id=data.profile_id,
        direction=data.direction
    )
    db.add(swipe)

    # Check for mutual like → create match
    matched = False
    match_id = None
    if data.direction in ("like", "superlike"):
        mutual = await db.execute(
            select(Swipe).where(
                Swipe.swiper_id == data.profile_id,
                Swipe.swiped_id == my_profile.id,
                Swipe.direction.in_(["like", "superlike"])
            )
        )
        if mutual.scalar_one_or_none():
            # Create the match (ensure consistent ordering)
            p1, p2 = sorted([str(my_profile.id), str(data.profile_id)])
            match = Match(profile_1_id=UUID(p1), profile_2_id=UUID(p2))
            db.add(match)
            await db.flush()
            match_id = match.id
            matched = True
            logger.info(f"Match created: {p1} ↔ {p2}")

    await db.commit()
    return SwipeResponse(
        matched=matched,
        match_id=match_id,
        message="It's a match! 💜" if matched else "Swiped!"
    )


@matches_router.get("", response_model=List[MatchResponse])
async def get_matches(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all active matches for the current user."""
    my_result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    my_profile = my_result.scalar_one_or_none()
    if not my_profile:
        return []

    result = await db.execute(
        select(Match).where(
            and_(
                or_(Match.profile_1_id == my_profile.id,
                    Match.profile_2_id == my_profile.id),
                Match.is_active == True
            )
        ).order_by(Match.last_message_at.desc().nullslast(), Match.matched_at.desc())
    )
    matches = result.scalars().all()

    response = []
    for match in matches:
        other_id = match.other_profile_id(my_profile.id)
        other_result = await db.execute(
            select(Profile).options(selectinload(Profile.photos))
            .where(Profile.id == other_id)
        )
        other = other_result.scalar_one_or_none()
        if not other:
            continue

        primary = next((p for p in other.photos if p.is_primary), None) or (other.photos[0] if other.photos else None)
        primary_photo = PhotoResponse(
            id=primary.id, url=primary.url,
            thumbnail_url=primary.thumbnail_url,
            is_primary=primary.is_primary,
            sort_order=primary.sort_order
        ) if primary else None

        # Count unread messages
        unread_result = await db.execute(
            select(Message).where(
                Message.match_id == match.id,
                Message.sender_id != my_profile.id,
                Message.is_read == False,
                Message.deleted_at.is_(None)
            )
        )
        unread_count = len(unread_result.scalars().all())

        response.append(MatchResponse(
            id=match.id,
            matched_at=match.matched_at,
            is_active=match.is_active,
            last_message_at=match.last_message_at,
            other_profile=MatchedProfileSnippet(
                id=other.id,
                first_name=other.first_name,
                age=other.age,
                primary_photo=primary_photo
            ),
            unread_count=unread_count
        ))
    return response


@matches_router.delete("/{match_id}", status_code=204)
async def unmatch(
    match_id: UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Unmatch (deactivate) a match."""
    my_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    my_profile = my_result.scalar_one_or_none()
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            or_(Match.profile_1_id == my_profile.id, Match.profile_2_id == my_profile.id)
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    match.is_active = False
    await db.commit()


# ══════════════════════════════════════════
# MESSAGES ROUTER
# ══════════════════════════════════════════
messages_router = APIRouter()


async def _verify_match_access(match_id: UUID, user: User, db: AsyncSession):
    """Helper — confirm user is part of this match."""
    my_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    my_profile = my_result.scalar_one_or_none()
    if not my_profile:
        raise HTTPException(status_code=400, detail="Profile not found")

    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.is_active == True,
            or_(Match.profile_1_id == my_profile.id,
                Match.profile_2_id == my_profile.id)
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match, my_profile


@messages_router.get("/{match_id}", response_model=ConversationResponse)
async def get_messages(
    match_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, le=50),
    current_user: User = Depends(get_current_verified_user),
    subscription: Subscription = Depends(get_current_subscription),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a match conversation."""
    match, my_profile = await _verify_match_access(match_id, current_user, db)

    # Free tier: limited messages per match
    if not subscription.is_premium:
        count_result = await db.execute(
            select(Message).where(
                Message.match_id == match_id,
                Message.deleted_at.is_(None)
            )
        )
        total_msgs = len(count_result.scalars().all())
        if total_msgs > settings.FREE_MESSAGES_PER_MATCH:
            raise HTTPException(
                status_code=402,
                detail=f"Upgrade to Mellow to continue this conversation beyond {settings.FREE_MESSAGES_PER_MATCH} messages."
            )

    result = await db.execute(
        select(Message).where(
            Message.match_id == match_id,
            Message.deleted_at.is_(None)
        ).order_by(Message.created_at.asc())
        .offset((page - 1) * limit).limit(limit)
    )
    msgs = result.scalars().all()

    # Mark unread messages as read
    await db.execute(
        update(Message).where(
            Message.match_id == match_id,
            Message.sender_id != my_profile.id,
            Message.is_read == False
        ).values(is_read=True, read_at=datetime.utcnow())
    )
    await db.commit()

    other_id = match.other_profile_id(my_profile.id)
    other_result = await db.execute(
        select(Profile).options(selectinload(Profile.photos))
        .where(Profile.id == other_id)
    )
    other = other_result.scalar_one_or_none()
    primary = next((p for p in other.photos if p.is_primary), None) if other else None

    return ConversationResponse(
        match_id=match_id,
        other_profile=MatchedProfileSnippet(
            id=other.id, first_name=other.first_name, age=other.age,
            primary_photo=PhotoResponse(
                id=primary.id, url=primary.url,
                thumbnail_url=primary.thumbnail_url,
                is_primary=primary.is_primary,
                sort_order=primary.sort_order
            ) if primary else None
        ),
        messages=[
            MessageResponse(
                id=m.id, match_id=m.match_id, sender_id=m.sender_id,
                content=m.content, message_type=m.message_type,
                is_read=m.is_read, read_at=m.read_at, created_at=m.created_at,
                is_mine=(m.sender_id == my_profile.id)
            ) for m in msgs
        ],
        total=len(msgs)
    )


@messages_router.post("/{match_id}", response_model=MessageResponse, status_code=201)
async def send_message(
    match_id: UUID,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a match conversation."""
    match, my_profile = await _verify_match_access(match_id, current_user, db)

    message = Message(
        match_id=match_id,
        sender_id=my_profile.id,
        content=data.content,
        message_type=data.message_type,
    )
    db.add(message)
    match.last_message_at = datetime.utcnow()
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id, match_id=message.match_id,
        sender_id=message.sender_id, content=message.content,
        message_type=message.message_type, is_read=message.is_read,
        read_at=message.read_at, created_at=message.created_at,
        is_mine=True
    )


# ══════════════════════════════════════════
# SUBSCRIPTIONS ROUTER
# ══════════════════════════════════════════
subscriptions_router = APIRouter()

PLANS = [
    PlanResponse(
        id="free", name="Free", price_monthly=0.0, stripe_price_id="",
        features=PlanFeatures(
            daily_swipes=10, messages_per_match=3, max_photos=2,
            advanced_filters=False, read_receipts=False,
            see_who_liked_you=False, boosts_per_month=0, priority_discovery=False
        )
    ),
    PlanResponse(
        id="mellow", name="Mellow", price_monthly=14.99,
        stripe_price_id=settings.STRIPE_KINDRED_PRICE_ID,
        features=PlanFeatures(
            daily_swipes="unlimited", messages_per_match="unlimited",
            max_photos=6, advanced_filters=True, read_receipts=True,
            see_who_liked_you=False, boosts_per_month=1, priority_discovery=False
        )
    ),
    PlanResponse(
        id="mellow_plus", name="Mellow Plus", price_monthly=29.99,
        stripe_price_id=settings.STRIPE_KINDRED_PLUS_PRICE_ID,
        features=PlanFeatures(
            daily_swipes="unlimited", messages_per_match="unlimited",
            max_photos=6, advanced_filters=True, read_receipts=True,
            see_who_liked_you=True, boosts_per_month=3, priority_discovery=True
        )
    ),
]


@subscriptions_router.get("/plans", response_model=List[PlanResponse])
async def get_plans():
    """Get all available subscription plans."""
    return PLANS


@subscriptions_router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    subscription: Subscription = Depends(get_current_subscription)
):
    """Get the current user's subscription status."""
    return SubscriptionResponse(
        plan=subscription.plan, status=subscription.status,
        is_premium=subscription.is_premium, is_plus=subscription.is_plus,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end
    )


@subscriptions_router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    plan_id: str,
    current_user: User = Depends(get_current_verified_user),
    subscription: Subscription = Depends(get_current_subscription),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe checkout session for plan upgrade."""
    plan = next((p for p in PLANS if p.id == plan_id and p.id != "free"), None)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Get or create Stripe customer
        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={"user_id": str(current_user.id)}
            )
            subscription.stripe_customer_id = customer.id
            await db.commit()

        session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/subscription",
            metadata={"user_id": str(current_user.id), "plan": plan_id}
        )
        return CheckoutSessionResponse(checkout_url=session.url, session_id=session.id)

    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail="Payment setup failed. Please try again.")


@subscriptions_router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events."""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload   = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        user_id  = session["metadata"]["user_id"]
        plan     = session["metadata"]["plan"]
        sub_id   = session.get("subscription")

        stripe_sub = stripe.Subscription.retrieve(sub_id)
        await db.execute(
            update(Subscription)
            .where(Subscription.user_id == UUID(user_id))
            .values(
                plan=plan, status="active",
                stripe_sub_id=sub_id,
                current_period_start=datetime.fromtimestamp(stripe_sub["current_period_start"]),
                current_period_end=datetime.fromtimestamp(stripe_sub["current_period_end"]),
            )
        )
        await db.commit()
        logger.info(f"Subscription activated: user={user_id} plan={plan}")

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        await db.execute(
            update(Subscription)
            .where(Subscription.stripe_sub_id == sub["id"])
            .values(plan="free", status="cancelled")
        )
        await db.commit()

    return {"received": True}


# ══════════════════════════════════════════
# SAFETY ROUTER
# ══════════════════════════════════════════
safety_router = APIRouter()


@safety_router.post("/report", response_model=SafetyResponse)
async def report_user(
    data: ReportRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Report another user for inappropriate behaviour."""
    if data.reported_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot report yourself")

    report = Report(
        reporter_id=current_user.id,
        reported_id=data.reported_user_id,
        reason=data.reason,
        description=data.description
    )
    db.add(report)
    await db.commit()
    logger.info(f"Report filed: {current_user.id} → {data.reported_user_id} [{data.reason}]")
    return SafetyResponse(success=True, message="Report submitted. Our team will review it shortly.")


@safety_router.post("/block", response_model=SafetyResponse)
async def block_user(
    data: BlockRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Block another user — they won't appear in your discovery or messages."""
    if data.blocked_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    existing = await db.execute(
        select(Block).where(
            Block.blocker_id == current_user.id,
            Block.blocked_id == data.blocked_user_id
        )
    )
    if existing.scalar_one_or_none():
        return SafetyResponse(success=True, message="User is already blocked")

    block = Block(blocker_id=current_user.id, blocked_id=data.blocked_user_id)
    db.add(block)

    # Deactivate any existing match with this user
    my_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    my_profile = my_result.scalar_one_or_none()
    if my_profile:
        other_result = await db.execute(select(Profile).where(Profile.user_id == data.blocked_user_id))
        other_profile = other_result.scalar_one_or_none()
        if other_profile:
            await db.execute(
                update(Match).where(
                    or_(
                        and_(Match.profile_1_id == my_profile.id,  Match.profile_2_id == other_profile.id),
                        and_(Match.profile_1_id == other_profile.id, Match.profile_2_id == my_profile.id)
                    )
                ).values(is_active=False)
            )

    await db.commit()
    return SafetyResponse(success=True, message="User blocked successfully.")


@safety_router.delete("/block/{user_id}", response_model=SafetyResponse)
async def unblock_user(
    user_id: UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Unblock a previously blocked user."""
    result = await db.execute(
        select(Block).where(Block.blocker_id == current_user.id, Block.blocked_id == user_id)
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    await db.delete(block)
    await db.commit()
    return SafetyResponse(success=True, message="User unblocked.")


# ── Export routers with standard names ────────────────────────
router = matches_router   # used by matches prefix in main.py

# Additional routers registered separately in main.py

@matches_router.get("/liked-me")
async def get_who_liked_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get profiles that liked you.
    Free in test mode — will be Premium only in production.
    """
    from sqlalchemy.orm import selectinload

    # Get current user's profile
    my_result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    my_profile = my_result.scalar_one_or_none()
    if not my_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Find all profiles that liked or superliked you
    result = await db.execute(
        select(Swipe)
        .where(
            Swipe.swiped_id == my_profile.id,
            Swipe.direction.in_(["like", "superlike"])
        )
        .order_by(Swipe.created_at.desc())
    )
    swipes = result.scalars().all()

    if not swipes:
        return []

    # Get their profiles
    liker_ids = [s.swiper_id for s in swipes]
    profiles_result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.id.in_(liker_ids))
    )
    profiles = profiles_result.scalars().all()

    return [
        {
            "id":            str(p.id),
            "first_name":    p.first_name,
            "age":           p.age,
            "occupation":    p.occupation,
            "location_city": p.location_city,
            "bio":           p.bio,
            "photos": [
                {
                    "id":            str(ph.id),
                    "url":           ph.url,
                    "thumbnail_url": ph.thumbnail_url or ph.url,
                    "is_primary":    ph.is_primary,
                    "sort_order":    ph.sort_order,
                }
                for ph in sorted(p.photos, key=lambda x: x.sort_order)
            ],
            "swiped_direction": next(
                (s.direction for s in swipes if s.swiper_id == p.id), "like"
            ),
        }
        for p in profiles
    ]

