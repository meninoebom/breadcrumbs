import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
API_KEY = os.getenv("API_KEY", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 30


def verify_admin_password(password: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    return hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode())


def create_access_token() -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {"exp": expires, "sub": "admin"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def require_admin(
    authorization: str = Header(None),
    x_api_key: str = Header(None),
) -> None:
    # API key auth (for machine clients like NanoClaw)
    if x_api_key:
        if API_KEY and hmac.compare_digest(x_api_key.encode(), API_KEY.encode()):
            return
        raise HTTPException(status_code=401, detail="Invalid API key")

    # JWT Bearer auth (for browser sessions)
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="Auth not configured")

    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
