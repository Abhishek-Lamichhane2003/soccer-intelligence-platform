from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import settings


def _password_material(password: str) -> bytes:
    """Return fixed-size bcrypt input so Unicode/long passwords never hit bcrypt's 72-byte limit."""
    return sha256(password.encode('utf-8')).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_material(password), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    encoded_hash = password_hash.encode('utf-8')
    try:
        if bcrypt.checkpw(_password_material(password), encoded_hash):
            return True
    except ValueError:
        return False

    # Compatibility with users created by pre-v5 local builds, which hashed raw UTF-8 directly.
    raw = password.encode('utf-8')
    if len(raw) <= 72:
        try:
            return bcrypt.checkpw(raw, encoded_hash)
        except ValueError:
            return False
    return False


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_minutes)
    payload = {
        'sub': subject,
        'iat': now,
        'nbf': now,
        'exp': exp,
        'iss': settings.jwt_issuer,
        'aud': settings.jwt_audience,
        'jti': uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={'require': ['exp', 'iat', 'sub', 'iss', 'aud']},
    )
