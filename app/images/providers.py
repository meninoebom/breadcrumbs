"""Concrete providers for theme image generation: Claude, Replicate, R2.

Each provider is constructed once and wired into the service at the
factory layer. All failures are translated into ImageGenerationError
or ImageCommitError so the service and API layers stay decoupled from
vendor-specific exceptions.
"""

import logging
import os
import uuid
from typing import Callable, List, Sequence
from urllib.parse import urlparse

import anthropic
import httpx
import replicate
import replicate.exceptions

from app.images.errors import ImageCommitError, ImageGenerationError
from app.storage import put_object

logger = logging.getLogger(__name__)


# ---------- Claude visualizer ----------

VISUALIZER_SYSTEM_PROMPT = """\
You translate abstract writing into concrete visual scenes for an image generator.

Given a theme (a short piece of writing) and optional tags, describe ONE vivid, \
renderable scene in 1-2 sentences. The scene should show concrete subjects \
(people, objects, machines, environments), a clear composition, and a mood \
aligned with the theme.

Rules:
- Describe what an observer would SEE. Start with a concrete noun phrase.
- Translate abstract concepts into visual metaphors. "Autonomy" might become \
"a single machine alone in a quiet glass room"; "attention" might become \
"a figure leaning forward over a steaming cup."
- Do NOT repeat the theme's phrasing verbatim. Interpret, don't echo.
- Do NOT use meta-language ("a painting showing X", "an image of Y"). Just the scene.
- Do NOT include any style or medium notes — those are added downstream.
- 1-2 sentences max. No preamble, no markdown.
"""

DEFAULT_VISUALIZER_MODEL = "claude-haiku-4-5-20251001"


class ClaudeVisualizer:
    """Uses Claude to translate abstract theme text into a concrete scene description."""

    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str = DEFAULT_VISUALIZER_MODEL,
        max_tokens: int = 200,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def describe_scene(self, theme_body: str, tag_names: Sequence[str]) -> str:
        tags_line = (
            f"Tags: {', '.join(tag_names)}" if tag_names else "Tags: (none)"
        )
        user_message = (
            f"Theme: {theme_body.strip()}\n{tags_line}\n\n"
            "Describe one concrete scene."
        )
        try:
            response = self._client.messages.create(
                model=self._model,
                system=VISUALIZER_SYSTEM_PROMPT,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APIError as e:
            logger.error("Claude visualizer API error: %s", e)
            raise ImageGenerationError(f"Visualizer error: {e}") from e

        if not response.content:
            raise ImageGenerationError("Visualizer returned empty response")

        scene = response.content[0].text.strip()
        if not scene:
            raise ImageGenerationError("Visualizer returned empty scene")
        return scene


# ---------- Replicate image generator ----------

DEFAULT_FLUX_MODEL = "black-forest-labs/flux-schnell"


class ReplicateImageGenerator:
    """Calls Flux Schnell on Replicate; returns temporary candidate URLs."""

    def __init__(
        self,
        model: str = DEFAULT_FLUX_MODEL,
        aspect_ratio: str = "1:1",
        num_outputs: int = 4,
        runner: Callable[..., list] = replicate.run,
    ) -> None:
        self._model = model
        self._aspect_ratio = aspect_ratio
        self._num_outputs = num_outputs
        self._runner = runner

    def generate(self, prompt: str) -> List[str]:
        if not os.getenv("REPLICATE_API_TOKEN"):
            raise ImageGenerationError("REPLICATE_API_TOKEN is not set")

        try:
            output = self._runner(
                self._model,
                input={
                    "prompt": prompt,
                    "num_outputs": self._num_outputs,
                    "aspect_ratio": self._aspect_ratio,
                    "output_format": "webp",
                    "output_quality": 90,
                },
            )
        except replicate.exceptions.ReplicateError as e:
            logger.error("Replicate API error: %s (prompt_len=%d)", e, len(prompt))
            raise ImageGenerationError(f"Replicate error: {e}") from e
        except httpx.HTTPError as e:
            logger.error("Replicate network error: %s", e)
            raise ImageGenerationError(f"Network error contacting Replicate: {e}") from e

        urls = [str(item.url) if hasattr(item, "url") else str(item) for item in output]
        if not urls:
            logger.error("Replicate returned empty output (prompt_len=%d)", len(prompt))
            raise ImageGenerationError("Replicate returned no candidates")
        return urls


# ---------- R2 image store ----------

DEFAULT_ALLOWED_HOSTS = frozenset({"replicate.delivery", "pbxt.replicate.delivery"})

CONTENT_TYPE_EXTENSIONS = {
    "image/webp": ".webp",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

IMAGE_MAGIC_BYTES = (
    b"RIFF",          # webp starts with RIFF (followed by "WEBP" at offset 8)
    b"\x89PNG",       # png
    b"\xff\xd8\xff",  # jpeg
)


class R2ImageStore:
    """Downloads an allowlisted source URL, validates the payload, uploads to R2."""

    def __init__(
        self,
        allowed_hosts: frozenset = DEFAULT_ALLOWED_HOSTS,
        fetch: Callable[..., httpx.Response] = httpx.get,
        put: Callable[[str, bytes, str], str] = put_object,
    ) -> None:
        self._allowed_hosts = allowed_hosts
        self._fetch = fetch
        self._put = put

    def commit(self, source_url: str) -> str:
        if not self._is_allowed_source(source_url):
            raise ImageCommitError(
                f"source_url host not in allowlist: {urlparse(source_url).hostname}"
            )

        try:
            response = self._fetch(source_url, follow_redirects=False, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Failed to download candidate from %s: %s", source_url, e)
            raise ImageCommitError(f"Could not download candidate: {e}") from e

        data = response.content
        content_type = response.headers.get("content-type", "").split(";")[0].strip()

        ext = CONTENT_TYPE_EXTENSIONS.get(content_type)
        if ext is None:
            logger.error("Rejecting unknown content-type from %s: %s", source_url, content_type)
            raise ImageCommitError(f"Unsupported content-type: {content_type!r}")

        if not any(data.startswith(magic) for magic in IMAGE_MAGIC_BYTES):
            logger.error("Payload from %s did not match image magic bytes", source_url)
            raise ImageCommitError("Downloaded payload is not a recognized image")

        key = f"theme-{uuid.uuid4().hex[:12]}{ext}"
        return self._put(key, data, content_type)

    def _is_allowed_source(self, source_url: str) -> bool:
        parsed = urlparse(source_url)
        if parsed.scheme != "https":
            return False
        host = parsed.hostname or ""
        return host in self._allowed_hosts or any(
            host.endswith(f".{h}") for h in self._allowed_hosts
        )
