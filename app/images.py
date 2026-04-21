"""Theme cover image generation via Replicate (Flux Schnell) + R2 storage."""

import logging
import os
import uuid
from typing import List
from urllib.parse import urlparse

import httpx
import replicate
import replicate.exceptions
from dotenv import load_dotenv

from app.models import Theme
from app.storage import put_object

load_dotenv()

logger = logging.getLogger(__name__)


FLUX_SCHNELL_MODEL = "black-forest-labs/flux-schnell"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_NUM_OUTPUTS = 4

# Replicate delivery hosts — allowlist for SSRF defense on commit.
ALLOWED_SOURCE_HOSTS = frozenset({"replicate.delivery", "pbxt.replicate.delivery"})

# Content-type → extension map. Unknown types are rejected rather than defaulted,
# so we don't silently store non-image bytes as .webp.
CONTENT_TYPE_EXTENSIONS = {
    "image/webp": ".webp",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

# Magic bytes for the formats we accept.
IMAGE_MAGIC_BYTES = (
    b"RIFF",       # webp (followed by size + "WEBP" at offset 8)
    b"\x89PNG",    # png
    b"\xff\xd8\xff",  # jpeg
)

STYLE_SUFFIX = (
    "Rendered as a flat oil painting in a limited three-color palette, "
    "figurative and confident, contemporary museum-quality painting. "
    "When human figures appear, depict a diversity of people — "
    "including people of color, varied ages, and varied body types. "
    "Tone balanced between gravity and play."
)


class ImageGenerationError(RuntimeError):
    """Upstream Replicate error — transient, tell the writer to retry."""


class ImageCommitError(RuntimeError):
    """Error downloading or validating a chosen candidate image."""


def build_theme_prompt(theme: Theme, tag_names: List[str]) -> str:
    """Translate a theme + tags into a natural-language Flux prompt.

    Scene framing + theme snippet + tag mood + fixed style suffix.
    """
    body = (theme.body_md or "").strip()
    first_sentence = body.split(".")[0].strip()
    snippet = first_sentence if 0 < len(first_sentence) <= 200 else body[:200].strip()

    tags_phrase = ""
    if tag_names:
        readable = ", ".join(name.replace("-", " ") for name in tag_names)
        tags_phrase = f" Mood draws from: {readable}."

    return (
        f'A single figurative scene that evokes the theme: "{snippet}".'
        f"{tags_phrase} {STYLE_SUFFIX}"
    )


def generate_candidate_images(
    prompt: str,
    num_outputs: int = DEFAULT_NUM_OUTPUTS,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
) -> List[str]:
    """Call Flux Schnell on Replicate, return a list of temporary image URLs."""
    if not os.getenv("REPLICATE_API_TOKEN"):
        raise ImageGenerationError("REPLICATE_API_TOKEN is not set")

    try:
        output = replicate.run(
            FLUX_SCHNELL_MODEL,
            input={
                "prompt": prompt,
                "num_outputs": num_outputs,
                "aspect_ratio": aspect_ratio,
                "output_format": "webp",
                "output_quality": 90,
            },
        )
    except replicate.exceptions.ReplicateError as e:
        logger.error("Replicate API error: %s (prompt_len=%d)", e, len(prompt))
        raise ImageGenerationError(f"Replicate error: {e}") from e
    except httpx.HTTPError as e:
        logger.error("Replicate network error: %s (prompt_len=%d)", e, len(prompt))
        raise ImageGenerationError(f"Network error contacting Replicate: {e}") from e

    urls = [str(item.url) if hasattr(item, "url") else str(item) for item in output]
    if not urls:
        logger.error("Replicate returned empty output (prompt_len=%d)", len(prompt))
        raise ImageGenerationError("Replicate returned no candidates")
    return urls


def _is_allowed_source(source_url: str) -> bool:
    """Validate source_url is HTTPS and hosted on an allowlisted Replicate domain."""
    parsed = urlparse(source_url)
    if parsed.scheme != "https":
        return False
    host = parsed.hostname or ""
    return host in ALLOWED_SOURCE_HOSTS or any(
        host.endswith(f".{h}") for h in ALLOWED_SOURCE_HOSTS
    )


def _looks_like_image(data: bytes) -> bool:
    return any(data.startswith(magic) for magic in IMAGE_MAGIC_BYTES)


def commit_image_to_r2(source_url: str) -> str:
    """Download an allowlisted Replicate URL and re-upload to R2.

    Rejects non-HTTPS URLs, hosts outside the Replicate allowlist, redirects,
    unknown content types, and payloads that don't start with a known image
    magic-byte sequence. Returns the permanent public R2 URL.
    """
    if not _is_allowed_source(source_url):
        raise ImageCommitError(
            f"source_url host not in allowlist: {urlparse(source_url).hostname}"
        )

    try:
        response = httpx.get(source_url, follow_redirects=False, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Failed to download candidate image from %s: %s", source_url, e)
        raise ImageCommitError(f"Could not download candidate: {e}") from e

    data = response.content
    content_type = response.headers.get("content-type", "").split(";")[0].strip()

    ext = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if ext is None:
        logger.error("Rejecting unknown content-type from %s: %s", source_url, content_type)
        raise ImageCommitError(f"Unsupported content-type: {content_type!r}")

    if not _looks_like_image(data):
        logger.error("Payload from %s did not match image magic bytes", source_url)
        raise ImageCommitError("Downloaded payload is not a recognized image")

    key = f"theme-{uuid.uuid4().hex[:12]}{ext}"
    return put_object(key, data, content_type)


def tags_for_prompt(theme: Theme) -> List[str]:
    """Extract tag names safely; theme.tags may be empty or not loaded."""
    return [t.name for t in (theme.tags or [])]
