"""
Mellow — Email Service (Resend)
Transactional emails via Resend's REST API.
Switched from SendGrid due to phone-verification signup wall.
"""

import logging
import httpx
from typing import Optional
from app.config import settings

logger = logging.getLogger("mellow.email")

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:

    @staticmethod
    async def _send(to_email: str, subject: str, html_body: str) -> bool:
        """Core send function via Resend's REST API."""
        if not settings.RESEND_API_KEY:
            logger.warning(f"[EMAIL SKIPPED — no API key] To: {to_email} | {subject}")
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>",
                        "to": [to_email],
                        "subject": subject,
                        "html": html_body,
                    },
                )
            success = response.status_code in (200, 201)
            if success:
                logger.info(f"Email sent: {subject} → {to_email}")
            else:
                logger.error(
                    f"Email failed [{response.status_code}]: {to_email} — {response.text}"
                )
            return success
        except Exception as e:
            logger.error(f"Resend error: {e}")
            return False

    # ── Verification Email ─────────────────────────────────────
    @staticmethod
    async def send_verification_email(to_email: str, token: str) -> bool:
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px">
          <h1 style="color:#3D2645;font-size:28px;margin-bottom:4px">🌿 Mellow</h1>
          <p style="color:#6b7280;font-size:13px;margin-bottom:28px">
            Calm, intentional dating for the next chapter of your life.
          </p>
          <h2 style="color:#111;font-size:20px">Verify your email address</h2>
          <p style="color:#374151;line-height:1.6">
            Welcome! Click the button below to verify your email and start your Mellow journey.
          </p>
          <a href="{verify_url}"
             style="display:inline-block;margin:24px 0;padding:14px 32px;
                    background:#C9705E;color:#fff;border-radius:8px;
                    text-decoration:none;font-weight:600;font-size:15px">
            Verify Email Address
          </a>
          <p style="color:#9ca3af;font-size:12px">
            This link expires in 24 hours. If you didn't create an account, ignore this email.
          </p>
        </div>"""
        return await EmailService._send(to_email, "Verify your Mellow email", html)

    # ── Password Reset ─────────────────────────────────────────
    @staticmethod
    async def send_reset_email(to_email: str, token: str) -> bool:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px">
          <h1 style="color:#3D2645;font-size:28px">🌿 Mellow</h1>
          <h2 style="color:#111;font-size:20px">Reset your password</h2>
          <p style="color:#374151;line-height:1.6">
            We received a request to reset your password. Click below to choose a new one.
          </p>
          <a href="{reset_url}"
             style="display:inline-block;margin:24px 0;padding:14px 32px;
                    background:#C9705E;color:#fff;border-radius:8px;
                    text-decoration:none;font-weight:600;font-size:15px">
            Reset Password
          </a>
          <p style="color:#9ca3af;font-size:12px">
            This link expires in 1 hour. If you didn't request this, ignore this email.
          </p>
        </div>"""
        return await EmailService._send(to_email, "Reset your Mellow password", html)

    # ── Match Notification ─────────────────────────────────────
    @staticmethod
    async def send_match_notification(to_email: str, match_name: str) -> bool:
        app_url = f"{settings.FRONTEND_URL}/messages"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px">
          <h1 style="color:#3D2645;font-size:28px">🌿 Mellow</h1>
          <h2 style="color:#111;font-size:22px">You have a new match!</h2>
          <p style="color:#374151;font-size:16px;line-height:1.6">
            You and <strong>{match_name}</strong> liked each other. 🎉<br/>
            Say hello and start a conversation!
          </p>
          <a href="{app_url}"
             style="display:inline-block;margin:24px 0;padding:14px 32px;
                    background:#C9705E;color:#fff;border-radius:8px;
                    text-decoration:none;font-weight:600;font-size:15px">
            Send a Message
          </a>
        </div>"""
        return await EmailService._send(to_email, f"🌿 You matched with {match_name}!", html)

    # ── Welcome Email ──────────────────────────────────────────
    @staticmethod
    async def send_welcome_email(to_email: str, first_name: str) -> bool:
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px">
          <h1 style="color:#3D2645;font-size:28px">🌿 Mellow</h1>
          <h2 style="color:#111;font-size:20px">Welcome, {first_name}!</h2>
          <p style="color:#374151;line-height:1.6">
            We're glad you're here. Mellow is designed for people who know what
            they want from a relationship — and aren't afraid to be patient finding it.
          </p>
          <a href="{settings.FRONTEND_URL}/profile"
             style="display:inline-block;margin:24px 0;padding:14px 32px;
                    background:#C9705E;color:#fff;border-radius:8px;
                    text-decoration:none;font-weight:600;font-size:15px">
            Complete My Profile
          </a>
        </div>"""
        return await EmailService._send(to_email, f"Welcome to Mellow, {first_name}! 🌿", html)