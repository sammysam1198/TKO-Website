import os
import re
import time
import hashlib
import secrets
import bcrypt
import jwt
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.(com|net|org|edu|gov|me)$", re.IGNORECASE)
USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")

_rate_limit_storage = defaultdict(list)
_rate_limit_lock = Lock()


def check_rate_limit(identifier: str, max_requests: int = 10, window: int = 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    with _rate_limit_lock:
        _rate_limit_storage[identifier] = [
            t for t in _rate_limit_storage[identifier] if now - t < window
        ]
        if len(_rate_limit_storage[identifier]) >= max_requests:
            return False
        _rate_limit_storage[identifier].append(now)
        return True


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def is_valid_username(username: str) -> bool:
    if "<" in username or ">" in username:
        return False
    return bool(USERNAME_REGEX.match(username))


def validate_password(password: str):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if "<" in password or ">" in password:
        return False, "Password cannot contain < or >"
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    return True, None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_auth_token(user: dict) -> str:
    secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_auth_token(token: str):
    secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    return jwt.decode(token, secret, algorithms=["HS256"])


def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


