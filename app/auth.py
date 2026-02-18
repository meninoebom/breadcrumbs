import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
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


def require_admin(authorization: str = Header(None)) -> None:
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
