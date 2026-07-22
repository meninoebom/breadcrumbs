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


# We enforce attempt bounds ourselves rather than delegating to the SDK, because
# replicate.run() cannot be bounded from outside: once its "Prefer: wait" window
# expires on a prediction that is still "starting", it falls into prediction.wait(),
# a poll loop with no timeout and no iteration cap. So we drive
# predictions.create(wait=False) and poll on our own clock.
#
# Two bounds, because "queued forever" and "slow" are different problems:
#
# - A prediction still in "starting" has not been scheduled onto a GPU at all. That
#   is the pool-wedge signature, and no amount of waiting fixes it, so we bail early
#   and fail over to the other pool.
# - Once it reaches "processing" it is genuinely rendering, and deserves real
#   patience. A healthy cold start was measured at 25s, so a bound anywhere near
#   that would cancel work that was about to succeed (and still bill us for it).
DEFAULT_STARTING_TIMEOUT_SECONDS = _env_number(
    "REPLICATE_STARTING_TIMEOUT_SECONDS", 15.0, float
)
DEFAULT_ATTEMPT_TIMEOUT_SECONDS = _env_number(
    "REPLICATE_ATTEMPT_TIMEOUT_SECONDS", 40.0, float
)
DEFAULT_MAX_ATTEMPTS = int(_env_number("REPLICATE_MAX_ATTEMPTS", 2, lambda v: int(v)))

# Caps how long any single HTTP call (create, poll, cancel) may block. The SDK's
# default read timeout is 30s, which is far longer than a poll needs and would let
# one wedged reload blow the attempt budget.
DEFAULT_HTTP_READ_TIMEOUT_SECONDS = _env_number(
    "REPLICATE_HTTP_READ_TIMEOUT_SECONDS", 10.0, float
)


class PredictionWedged(Exception):
    """A prediction never reached a terminal state within its attempt budget."""


# Account- or request-level failures: identical on every model, so failing over
# cannot help and only doubles the doomed calls. 402 in particular is Replicate's
# out-of-credit signal, which needs a top-up rather than another request.
#
# Everything else, including 404, is treated as model- or infrastructure-level and
# is worth trying on the next pool. 404 earns its place here empirically: Replicate
# returned "No adapter found for model" for a model that had succeeded minutes
# earlier, so it is not the permanent "no such model" a 404 usually implies.
UNRECOVERABLE_STATUSES = frozenset({400, 401, 402, 403, 422, 429})


def _is_retryable(error: BaseException) -> bool:
    """Is this worth spending another attempt (on the next model) on?"""
    if isinstance(error, PredictionWedged):
        return True
    if isinstance(error, replicate.exceptions.ModelError):
        return True  # CUDA OOM and friends; a re-roll usually lands somewhere healthy
    if isinstance(error, replicate.exceptions.ReplicateError):
        status = getattr(error, "status", None)
        if not isinstance(status, int):
            return False
        return status not in UNRECOVERABLE_STATUSES
    if isinstance(error, httpx.HTTPError):
        return True  # read timeout, connection reset: transport-level, not semantic
    return False


class ReplicateImageGenerator:
    """Generates candidates via parallel Flux Schnell predictions.

    Each candidate is its own prediction with ``num_outputs=1``, so a single CUDA OOM
    or stuck worker costs one candidate rather than the whole batch.

    Time is bounded at three levels, and the ordering is the invariant:

    1. ``starting_timeout_seconds`` catches a pool that accepted the prediction but
       never scheduled it. On expiry we cancel and fail over to the next model.
    2. ``attempt_timeout_seconds`` bounds an attempt that *is* rendering. We create
       non-blocking and poll ourselves, so this is a real bound rather than a
       request we hope the SDK honors. On expiry the prediction is cancelled;
       otherwise it keeps running on GPU and billing.
    3. ``timeout_seconds`` is a batch-wide wall-clock backstop, derived from (2) and
       ``max_attempts`` so it cannot be configured below the retry budget. It is a
       last resort: Python cannot cancel a running thread, so if a worker thread
       wedges anyway this is what lets the request return.
    """

    def __init__(
        self,
        models: Sequence[str] = DEFAULT_FLUX_MODELS,
        aspect_ratio: str = "1:1",
        num_outputs: int = 4,
        timeout_seconds: Optional[float] = None,
        starting_timeout_seconds: float = DEFAULT_STARTING_TIMEOUT_SECONDS,
        attempt_timeout_seconds: float = DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        http_read_timeout_seconds: float = DEFAULT_HTTP_READ_TIMEOUT_SECONDS,
        client: Optional[replicate.Client] = None,
    ) -> None:
        if not models:
            raise ValueError("models must not be empty")
        self._models = tuple(models)
        self._starting_timeout_seconds = starting_timeout_seconds
        self._aspect_ratio = aspect_ratio
        self._num_outputs = num_outputs
        self._attempt_timeout_seconds = attempt_timeout_seconds
        self._max_attempts = max_attempts
        self._http_read_timeout_seconds = http_read_timeout_seconds
        self._client = client
        # Worst realistic path: every attempt but the last gives up early as wedged,
        # and the last one runs its full budget. Each attempt can also overrun by at
        # most one in-flight HTTP call. Derived rather than hand-set, because a
        # backstop shorter than the retry budget silently makes retries unreachable,
        # which is the bug this class was rewritten to fix.
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else (
                (max_attempts - 1) * starting_timeout_seconds
                + attempt_timeout_seconds
                + max_attempts * http_read_timeout_seconds
            )
        )

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
            # num_outputs * timeout (4 * 60s = 4 minutes) to surface one error.
            deadline = time.monotonic() + self._timeout_seconds
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
        self._client = replicate.Client(
            api_token=token,
            timeout=httpx.Timeout(
                5.0,
                connect=5.0,
                read=self._http_read_timeout_seconds,
                write=self._http_read_timeout_seconds,
                pool=10.0,
            ),
        )
        return self._client

    def _generate_one(self, client: replicate.Client, prompt: str) -> str:
        last_error: Optional[BaseException] = None
        for attempt in range(1, self._max_attempts + 1):
            # Move to the next pool on each retry. When a pool wedges it stops
            # scheduling *everything*, so re-rolling against the same one just buys
            # another timeout; the other pool is usually healthy at that moment.
            model = self._models[(attempt - 1) % len(self._models)]
            try:
                return self._run_attempt(client, prompt, model)
            except (
                PredictionWedged,
                replicate.exceptions.ReplicateException,
                httpx.HTTPError,
            ) as e:
                if not _is_retryable(e):
                    raise ImageGenerationError(f"Replicate error: {e}") from e
                last_error = e
                logger.warning(
                    "Replicate attempt %d/%d on %s failed (%s): %s",
                    attempt, self._max_attempts, model, type(e).__name__, e,
                )

        raise ImageGenerationError(
            f"Failed after {self._max_attempts} attempts: {last_error}"
        ) from last_error

    def _run_attempt(self, client: replicate.Client, prompt: str, model: str) -> str:
        prediction = client.predictions.create(
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

        started = time.monotonic()
        scheduling_deadline = started + self._starting_timeout_seconds
        attempt_deadline = started + self._attempt_timeout_seconds
        while prediction.status not in TERMINAL_STATUSES:
            now = time.monotonic()
            # Read the status before cancelling; cancel() overwrites it.
            stuck_at = prediction.status
            if stuck_at == "starting" and now >= scheduling_deadline:
                self._abandon(prediction)
                raise PredictionWedged(
                    f"{model} never left 'starting' within "
                    f"{self._starting_timeout_seconds:.0f}s"
                )
            if now >= attempt_deadline:
                self._abandon(prediction)
                raise PredictionWedged(
                    f"{model} still {stuck_at} after "
                    f"{self._attempt_timeout_seconds:.0f}s"
                )
            time.sleep(client.poll_interval)
            prediction.reload()

        if prediction.status == "failed":
            # Matches replicate.run()'s own handling; ModelError is retryable.
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
