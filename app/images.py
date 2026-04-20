"""Theme cover image generation via Replicate (Flux Schnell) + R2 storage."""

import os
import uuid
from typing import List

import httpx
import replicate
from dotenv import load_dotenv

from app.models import Tag, Theme

load_dotenv()


FLUX_SCHNELL_MODEL = "black-forest-labs/flux-schnell"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_NUM_OUTPUTS = 4

STYLE_SUFFIX = (
    "Rendered as a flat oil painting in a limited three-color palette, "
    "figurative and confident, contemporary museum-quality painting. "
    "When human figures appear, depict a diversity of people — "
    "including people of color, varied ages, and varied body types. "
    "Tone balanced between gravity and play."
)


def build_theme_prompt(theme: Theme, tag_names: List[str]) -> str:
    """Translate a theme + its tags into a natural-language Flux prompt.

    Structure: scene framing + theme snippet + tag mood + fixed style suffix.
    The suffix is what makes every generated image feel like it belongs on crumb.blog.
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
    """Call Flux Schnell on Replicate, return a list of temporary image URLs.

    The returned URLs are served by Replicate and expire in ~1 hour — use them
    for preview in the UI, then call commit_image_to_r2() with the chosen one
    to get a permanent URL.
    """
    if not os.getenv("REPLICATE_API_TOKEN"):
        raise RuntimeError("REPLICATE_API_TOKEN is not set")

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
    # Replicate returns a list of FileOutput objects; .url gives the stable string.
    return [str(item.url) if hasattr(item, "url") else str(item) for item in output]


def commit_image_to_r2(source_url: str) -> str:
    """Download a temporary image URL and re-upload to R2 under a stable key.

    Returns the permanent public R2 URL.
    """
    import boto3

    response = httpx.get(source_url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    data = response.content
    content_type = response.headers.get("content-type", "image/webp")
    ext = {
        "image/webp": ".webp",
        "image/png": ".png",
        "image/jpeg": ".jpg",
    }.get(content_type, ".webp")

    key = f"theme-{uuid.uuid4().hex[:12]}{ext}"
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )
    s3.put_object(
        Bucket=os.getenv("R2_BUCKET_NAME"),
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"{os.getenv('R2_PUBLIC_URL', '').rstrip('/')}/{key}"


def tags_for_prompt(theme: Theme) -> List[str]:
    """Extract tag names safely; theme.tags may be empty."""
    return [t.name for t in (theme.tags or [])]
