"""
Mellow — Input Validators
Reusable validation functions across the app.
"""

import re
from typing import Optional


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def is_valid_password(password: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    return True, ""


def is_valid_phone(phone: str) -> bool:
    """Basic E.164 phone format check."""
    pattern = r"^\+?[1-9]\d{7,14}$"
    return bool(re.match(pattern, phone.replace(" ", "").replace("-", "")))


def sanitize_text(text: Optional[str], max_length: int = 500) -> Optional[str]:
    """Strip dangerous characters and trim to max length."""
    if not text:
        return None
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalise whitespace
    text = " ".join(text.split())
    return text[:max_length].strip() or None


def is_valid_image_type(content_type: str) -> bool:
    return content_type in ("image/jpeg", "image/png", "image/webp")


def is_valid_age(age: int) -> bool:
    return 30 <= age <= 80


def clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))
