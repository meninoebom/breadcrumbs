"""Concrete providers for theme image generation: Claude, Replicate, R2.

Each provider is constructed once and wired into the service at the
factory layer. All failures are translated into ImageGenerationError
or ImageCommitError so the service and API layers stay decoupled from
vendor-specific exceptions.
"""

import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, List, Optional, Sequence
from urllib.parse import urlparse

import anthropic
import httpx
import replicate
import replicate.exceptions
import replicate.prediction

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
"a middle-aged Filipina nurse leaning forward over a steaming cup."
- When the scene includes a person, name them with specific demographic detail — \
ethnicity, age, gender, build, distinguishing features — chosen to fit the theme. \
Don't default to one prototype (white, male, young, thin); across themes the \
rendered range should feel like the world. Vary skin tones, ages, gender \
presentations, and body types naturally, as the theme allows.
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

    def describe_scene(
        self,
        theme_body: str,
        tag_names: Sequence[str],
        breadcrumb_digest: str = "",
    ) -> str:
        tags_line = (
            f"Tags: {', '.join(tag_names)}" if tag_names else "Tags: (none)"
        )
        develops_block = (
            f"\n\nIt develops through these notes:\n{breadcrumb_digest.strip()}"
            if breadcrumb_digest.strip()
            else ""
        )
        user_message = (
            f"The theme opens with: {theme_body.strip()}\n{tags_line}"
            f"{develops_block}\n\n"
            "Describe one concrete scene that reflects the whole arc, not just the opening."
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

# Two pools running the same Flux Schnell weights. Both have had periods of
# accepting predictions and then never scheduling them, and crucially they fail at
# different times: "-lora" was the workaround when the canonical pool wedged in
# 2026-05, and by 2026-07 the positions had swapped (canonical healthy at 25s,
# "-lora" stuck in "starting" past 45s). So we treat the model as a failover list
# rather than a constant, and a retry moves to the *next pool* instead of re-rolling
# the dice on the one that just failed to schedule us.
#
# Both are called with num_outputs=1: "-lora" OOMs above 1, and one prediction per
# candidate is what isolates a single bad worker from the rest of the batch anyway.
DEFAULT_FLUX_MODELS = (
    "black-forest-labs/flux-schnell",
    "black-forest-labs/flux-schnell-lora",
)

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "canceled"})


def _env_number(name: str, default: float, cast: Callable[[str], float]) -> float:
    """Read a positive number from the environment, falling back loudly.

    These are module-level constants, so a bad value would otherwise crash app
    startup with a ValueError. A zero or negative value is worse than useless here:
    it disables the very bound it configures.
    """
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        logger.warning("%s=%r is not a number; using %s", name, raw, default)
        return default
    if value <= 0:
        logger.warning("%s=%r must be positive; using %s", name, raw, default)
        return default
    return value


# We drive predictions.create(wait=False) and poll on our own clock, because
# replicate.run() cannot be bounded from outside: once its "Prefer: wait" window
# expires on a prediction that is still "starting", it falls into prediction.wait(),
# a poll loop with no timeout and no iteration cap.
#
# ONE deadline, not two. An earlier version split "starting" (15s) from "processing"
# (40s) on the theory that a prediction still in "starting" had never been scheduled
# and was therefore wedged. Measurement disproved it: healthy Flux Schnell cold starts
# routinely sit in "starting" for 15-30s before they render, so the 15s bound cancelled
# work that was about to succeed and failed over to the sibling pool for no reason. A
# single generous deadline separates the cases cleanly — a real cold start finishes
# well under it; a genuinely wedged pool never leaves "starting" and simply hits it.
DEFAULT_TIMEOUT_SECONDS = _env_number("REPLICATE_TIMEOUT_SECONDS", 45.0, float)

# A create() call can fail transiently on one pool: Replicate has returned
# "No adapter found" 404s for a model that succeeded moments earlier. That is a blip on
# this pool, not a reason to abandon it for a possibly-dead sibling, so we re-create on
# the same pool up to this many times before failing over.
DEFAULT_CREATE_ATTEMPTS = int(_env_number("REPLICATE_CREATE_ATTEMPTS", 2, int))


class PredictionWedged(Exception):
    """A prediction never reached a terminal state within its deadline."""


# Account- or request-level create failures: the same on every pool, so retrying or
# failing over only doubles doomed calls. 402 is Replicate's out-of-credit signal (top
# up, don't retry), 401 a bad token, 400/422 a bad request, 429 a rate limit. Anything
# else — including 404 and 5xx — is transient or infra-level and worth another try.
UNRECOVERABLE_STATUSES = frozenset({400, 401, 402, 403, 422, 429})


def _is_unrecoverable(error: replicate.exceptions.ReplicateError) -> bool:
    """A create error that retrying or failing over cannot fix."""
    status = getattr(error, "status", None)
    return isinstance(status, int) and status in UNRECOVERABLE_STATUSES


class ReplicateImageGenerator:
    """Generates candidate images via parallel Flux Schnell predictions.

    Each candidate is its own prediction with ``num_outputs=1``, run concurrently, so
    one stuck or failed prediction costs a single candidate rather than the whole batch.
    ``generate`` returns every candidate that succeeded; the caller lets the user pick.

    Robustness is two simple rules, one per failure mode Replicate actually exhibits:

    - A ``create`` that fails transiently (e.g. a "No adapter found" 404) is retried on
      the *same* pool a few times before moving on — the pool is flaking, not down.
    - A prediction that is created but never finishes within ``timeout_seconds`` means
      the pool is wedged: we cancel it (so it stops billing) and fail over to the next
      pool.
    """

    def __init__(
        self,
        models: Sequence[str] = DEFAULT_FLUX_MODELS,
        aspect_ratio: str = "1:1",
        num_outputs: int = 4,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        create_attempts: int = DEFAULT_CREATE_ATTEMPTS,
        client: Optional[replicate.Client] = None,
    ) -> None:
        if not models:
            raise ValueError("models must not be empty")
        self._models = tuple(models)
        self._aspect_ratio = aspect_ratio
        self._num_outputs = num_outputs
        self._timeout_seconds = timeout_seconds
        self._create_attempts = create_attempts
        self._client = client
        # Batch safety net: a candidate tries every pool once, each bounded by
        # timeout_seconds, so its worst case is len(models) * timeout. Candidates run
        # concurrently, so the batch shares one deadline rather than summing theirs.
        self._batch_timeout_seconds = len(self._models) * timeout_seconds + 15.0

    def generate(self, prompt: str) -> List[str]:
        client = self._get_client()

        pool = ThreadPoolExecutor(max_workers=self._num_outputs)
        try:
            futures = [
                pool.submit(self._generate_one, client, prompt)
                for _ in range(self._num_outputs)
            ]
            urls: List[str] = []
            errors: List[str] = []
            # One deadline shared across all candidates. They were all submitted at
            # once and run concurrently, so the budget is batch-wide: giving each
            # future its own fresh timeout would let a fully-wedged pool take
            # num_outputs * timeout to surface one error.
            deadline = time.monotonic() + self._batch_timeout_seconds
            for future in futures:
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    urls.append(future.result(timeout=remaining))
                except FutureTimeoutError:
                    errors.append(f"gave up waiting after {remaining:.0f}s")
                except ImageGenerationError as e:
                    errors.append(str(e))
        finally:
            # Can't stop threads already running; cancel_futures only drops queued
            # work. Stragglers finish on their own and cancel their own predictions.
            pool.shutdown(wait=False, cancel_futures=True)

        if not urls:
            logger.error(
                "All %d Replicate candidates failed (prompt_len=%d): %s",
                self._num_outputs, len(prompt), errors,
            )
            raise ImageGenerationError(
                f"All {self._num_outputs} candidates failed: {'; '.join(errors)}"
            )
        if errors:
            logger.warning(
                "Partial Replicate failure: %d/%d candidates failed: %s",
                len(errors), self._num_outputs, errors,
            )
        return urls

    def _get_client(self) -> replicate.Client:
        if self._client is not None:
            return self._client
        token = os.getenv("REPLICATE_API_TOKEN")
        if not token:
            raise ImageGenerationError("REPLICATE_API_TOKEN is not set")
        # Cap any single HTTP call (create, poll, cancel) so one wedged request can't
        # blow the deadline. The SDK's 30s default read timeout is far longer than a
        # poll needs.
        self._client = replicate.Client(
            api_token=token,
            timeout=httpx.Timeout(5.0, connect=5.0, read=10.0, write=10.0, pool=10.0),
        )
        return self._client

    def _generate_one(self, client: replicate.Client, prompt: str) -> str:
        # Try each pool in order. Every failure is recorded so the caller can report
        # what actually happened on *both* pools, not just the last one.
        errors: List[str] = []
        for model in self._models:
            prediction = self._create(client, prompt, model, errors)
            if prediction is None:
                continue  # create kept failing transiently on this pool; fail over
            try:
                return self._await_result(client, prediction)
            except (
                PredictionWedged,
                replicate.exceptions.ReplicateException,
                httpx.HTTPError,
            ) as e:
                # Wedged, model error (CUDA OOM), or a poll blip: this pool isn't
                # delivering, so fail over to the next one.
                errors.append(f"{model}: {e}")
                logger.warning(
                    "Replicate on %s failed (%s): %s", model, type(e).__name__, e
                )
        raise ImageGenerationError("; ".join(errors) or "no pools available")

    def _create(
        self,
        client: replicate.Client,
        prompt: str,
        model: str,
        errors: List[str],
    ) -> Optional["replicate.prediction.Prediction"]:
        """Create a prediction, retrying transient failures on the same pool.

        Returns the prediction, or ``None`` if this pool should be failed over.
        Re-raises as ImageGenerationError for unrecoverable errors (bad token, out of
        credit) — those are the same on every pool, so there is nothing to fail over to.
        """
        for attempt in range(1, self._create_attempts + 1):
            try:
                return client.predictions.create(
                    model=model,
                    input={
                        "prompt": prompt,
                        "num_outputs": 1,
                        "aspect_ratio": self._aspect_ratio,
                        "output_format": "webp",
                        "output_quality": 90,
                    },
                    wait=False,
                )
            except replicate.exceptions.ReplicateError as e:
                if _is_unrecoverable(e):
                    raise ImageGenerationError(f"Replicate error: {e}") from e
                errors.append(f"{model} create failed (attempt {attempt}): {e}")
                logger.warning(
                    "Replicate create on %s failed (attempt %d/%d): %s",
                    model, attempt, self._create_attempts, e,
                )
            except httpx.HTTPError as e:
                errors.append(f"{model} create network error (attempt {attempt}): {e}")
                logger.warning(
                    "Replicate create on %s network error (attempt %d/%d): %s",
                    model, attempt, self._create_attempts, e,
                )
        return None

    def _await_result(
        self,
        client: replicate.Client,
        prediction: "replicate.prediction.Prediction",
    ) -> str:
        deadline = time.monotonic() + self._timeout_seconds
        while prediction.status not in TERMINAL_STATUSES:
            if time.monotonic() >= deadline:
                stuck_at = prediction.status  # read before cancel() overwrites it
                self._abandon(prediction)
                raise PredictionWedged(
                    f"did not finish within {self._timeout_seconds:.0f}s "
                    f"(stuck at '{stuck_at}')"
                )
            time.sleep(client.poll_interval)
            prediction.reload()

        if prediction.status == "failed":
            # Matches replicate.run()'s own handling; ModelError fails us over.
            raise replicate.exceptions.ModelError(prediction)
        if prediction.status == "canceled":
            raise ImageGenerationError("Prediction was canceled")

        return self._extract_url(prediction.output)

    def _abandon(self, prediction) -> None:  # type: ignore[no-untyped-def]
        """Cancel a prediction we have given up on so it stops billing.

        Best effort by design: this runs while we are already failing, and a cleanup
        error must never replace the error we actually want to report.
        """
        try:
            prediction.cancel()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Could not cancel abandoned prediction %s: %s",
                getattr(prediction, "id", "?"), e,
            )

    @staticmethod
    def _extract_url(output: object) -> str:
        # A prediction can report "succeeded" with no output attached; guard rather
        # than let list(None) raise TypeError, which would escape as a 500.
        if output is None:
            raise ImageGenerationError("Replicate returned no output")
        items = list(output) if isinstance(output, (list, tuple)) else [output]
        if not items:
            raise ImageGenerationError("Replicate returned empty output")
        item = items[0]
        return str(item.url) if hasattr(item, "url") else str(item)


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
