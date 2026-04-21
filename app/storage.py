"""Cloudflare R2 (S3-compatible) storage helpers for uploads and generated images."""

import logging
import os
from typing import Optional

import boto3
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REQUIRED_R2_VARS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_PUBLIC_URL",
)


class R2ConfigError(RuntimeError):
    """Raised when required R2 environment variables are missing."""


def assert_r2_env() -> None:
    missing = [v for v in REQUIRED_R2_VARS if not os.getenv(v)]
    if missing:
        raise R2ConfigError(f"Missing R2 env vars: {', '.join(missing)}")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def public_url(key: str) -> str:
    base: Optional[str] = os.getenv("R2_PUBLIC_URL")
    if not base:
        raise R2ConfigError("R2_PUBLIC_URL is not set")
    return f"{base.rstrip('/')}/{key}"


def put_object(key: str, body: bytes, content_type: str) -> str:
    """Upload bytes to R2 under `key` and return the permanent public URL."""
    assert_r2_env()
    _client().put_object(
        Bucket=os.getenv("R2_BUCKET_NAME"),
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    return public_url(key)
