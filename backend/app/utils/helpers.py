"""
Mellow — General Helpers & Utilities
Fixed: datetime.utcnow() used throughout.
"""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID
import math
import re


# ── Date / Time ────────────────────────────────────────────────
def utcnow() -> datetime:
    """Return UTC datetime (naive, consistent with PostgreSQL)."""
    return datetime.utcnow()


def time_ago(dt: datetime) -> str:
    """Return human-readable 'time ago' string."""
    now  = datetime.utcnow()
    diff = now - dt.replace(tzinfo=None) if dt.tzinfo else now - dt
    secs = int(diff.total_seconds())

    if secs < 60:    return "just now"
    if secs < 3600:  return f"{secs // 60}m ago"
    if secs < 86400: return f"{secs // 3600}h ago"
    if secs < 604800:return f"{secs // 86400}d ago"
    return dt.strftime("%d %b %Y")


# ── Distance ───────────────────────────────────────────────────
def haversine_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """Calculate great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def format_distance(km: float) -> str:
    if km < 1:   return f"{int(km * 1000)} m away"
    if km < 10:  return f"{km:.1f} km away"
    return f"{int(km)} km away"


# ── String Helpers ─────────────────────────────────────────────
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def truncate(
    text: str, max_len: int = 100, suffix: str = "..."
) -> str:
    if not text or len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def mask_email(email: str) -> str:
    parts = email.split("@")
    if len(parts) != 2:
        return "***@***.***"
    local = parts[0]
    masked = local[0] + "***" if len(local) > 1 else "***"
    return f"{masked}@{parts[1]}"


# ── UUID Helpers ───────────────────────────────────────────────
def safe_uuid(value: Any) -> Optional[UUID]:
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


# ── Pagination ─────────────────────────────────────────────────
def paginate(total: int, page: int, limit: int) -> dict:
    total_pages = math.ceil(total / limit) if limit > 0 else 0
    return {
        "total":       total,
        "page":        page,
        "limit":       limit,
        "total_pages": total_pages,
        "has_next":    page < total_pages,
        "has_prev":    page > 1,
    }
