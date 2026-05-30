"""
Authentication primitives: Argon2 password hashing, opaque-token hashing,
and JWT access/refresh token creation & verification.

Argon2 parameters are sourced from .env. No password, token, or secret is ever
logged. JWT errors surface as a generic ``TokenError`` to the caller.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

from config import settings

# Argon2id hasher configured from .env (time/memory/parallelism cost).
_password_hasher = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)


class TokenError(Exception):
    """Raised when a JWT is invalid, expired, or of the wrong type."""


# --------------------------------------------------------------------------- #
# Password hashing (Argon2)                                                    #
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Return an Argon2id hash for the given plaintext password."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2 hash. Never raises on mismatch."""
    try:
        return _password_hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the stored hash should be upgraded to current Argon2 parameters."""
    try:
        return _password_hasher.check_needs_rehash(hashed)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Opaque refresh-token hashing (only the hash is persisted)                    #
# --------------------------------------------------------------------------- #
def generate_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token (URL-safe)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Deterministic SHA-256 hash of an opaque token for DB storage/lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# JWT access tokens                                                            #
# --------------------------------------------------------------------------- #
def create_access_token(*, user_id: str | uuid.UUID, role: str) -> str:
    """Create a short-lived signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode & validate an access token, returning its claims. Raises TokenError."""
    try:
        claims = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise TokenError("Invalid or expired token") from exc
    if claims.get("type") != "access":
        raise TokenError("Wrong token type")
    return claims


def refresh_token_expiry() -> datetime:
    """Absolute expiry timestamp for a newly issued refresh token."""
    return datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
