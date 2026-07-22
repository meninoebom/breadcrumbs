"""Tests for app.images — service orchestration and provider internals.

Three layers, each tested in isolation:
- service.py: orchestration only, via fakes for all three protocols
- providers.py: concrete providers with their external clients mocked
- __init__.py: the factory wires prod deps; covered by endpoint tests
"""

import time
from typing import List, Sequence
from unittest.mock import MagicMock

import httpx
import pytest

from app.images import (
    GenerationResult,
    ImageCommitError,
    ImageGenerationError,
    STYLE_SUFFIX,
    ThemeImageService,
    compose_prompt,
)
from app.images.service import build_breadcrumb_digest
from app.images.providers import (
    ClaudeVisualizer,
    R2ImageStore,
    ReplicateImageGenerator,
)


# ========== Fakes ==========


class FakeVisualizer:
    def __init__(self, scene: str = "a quiet scene"):
        self.scene = scene
        self.calls: List[tuple] = []
        self.digests: List[str] = []

    def describe_scene(
        self,
        theme_body: str,
        tag_names: Sequence[str],
        breadcrumb_digest: str = "",
    ) -> str:
        self.calls.append((theme_body, tuple(tag_names)))
        self.digests.append(breadcrumb_digest)
        return self.scene


class FakeImageGenerator:
    def __init__(self, candidates: List[str] | None = None):
        self.candidates = candidates or [f"https://fake/{i}.webp" for i in range(4)]
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> List[str]:
        self.last_prompt = prompt
        return list(self.candidates)


class FakeImageStore:
    def __init__(self, permanent_url: str = "https://cdn.example/permanent.webp"):
        self.permanent_url = permanent_url
        self.committed: List[str] = []

    def commit(self, source_url: str) -> str:
        self.committed.append(source_url)
        return self.permanent_url


# ========== Service orchestration ==========


def _make_service(**overrides) -> ThemeImageService:
    return ThemeImageService(
        visualizer=overrides.get("visualizer", FakeVisualizer()),
        generator=overrides.get("generator", FakeImageGenerator()),
        store=overrides.get("store", FakeImageStore()),
        style_suffix=overrides.get("style_suffix", "STYLE"),
    )


def test_compose_prompt_joins_scene_and_style():
    assert compose_prompt("a scene", "the style") == "a scene the style"


def test_compose_prompt_trims_whitespace():
    assert compose_prompt("  scene  ", "  style  ") == "scene style"


def test_service_pipelines_visualize_then_generate():
    visualizer = FakeVisualizer(scene="a table under a window")
    generator = FakeImageGenerator(candidates=["https://x/1.webp", "https://x/2.webp"])
    service = _make_service(visualizer=visualizer, generator=generator)

    result = service.generate_candidates(
        theme_body="On attention", tag_names=["slowness"]
    )

    assert isinstance(result, GenerationResult)
    assert result.prompt == "a table under a window STYLE"
    assert result.candidates == ["https://x/1.webp", "https://x/2.webp"]
    assert visualizer.calls == [("On attention", ("slowness",))]
    assert generator.last_prompt == "a table under a window STYLE"


def test_service_passes_tag_names_through_to_visualizer():
    visualizer = FakeVisualizer()
    service = _make_service(visualizer=visualizer)
    service.generate_candidates(theme_body="x", tag_names=["a", "b", "c"])
    assert visualizer.calls[0][1] == ("a", "b", "c")


def test_service_accepts_empty_tag_names():
    visualizer = FakeVisualizer()
    service = _make_service(visualizer=visualizer)
    service.generate_candidates(theme_body="x", tag_names=[])
    assert visualizer.calls[0][1] == ()


def test_service_commit_delegates_to_store():
    store = FakeImageStore(permanent_url="https://cdn.example/out.webp")
    service = _make_service(store=store)

    url = service.commit_candidate("https://replicate.delivery/x/out.webp")

    assert url == "https://cdn.example/out.webp"
    assert store.committed == ["https://replicate.delivery/x/out.webp"]


def test_service_visualizer_errors_bubble_up():
    class BrokenVisualizer:
        def describe_scene(self, body, tags, breadcrumb_digest=""):
            raise ImageGenerationError("visualizer exploded")

    service = _make_service(visualizer=BrokenVisualizer())
    with pytest.raises(ImageGenerationError, match="visualizer exploded"):
        service.generate_candidates("x", [])


def test_service_generator_errors_bubble_up():
    class BrokenGenerator:
        def generate(self, prompt):
            raise ImageGenerationError("generator exploded")

    service = _make_service(generator=BrokenGenerator())
    with pytest.raises(ImageGenerationError, match="generator exploded"):
        service.generate_candidates("x", [])


def test_service_store_errors_bubble_up():
    class BrokenStore:
        def commit(self, source_url):
            raise ImageCommitError("store exploded")

    service = _make_service(store=BrokenStore())
    with pytest.raises(ImageCommitError, match="store exploded"):
        service.commit_candidate("https://replicate.delivery/x")


def test_style_suffix_is_non_empty():
    """Regression guard: the crumb.blog visual identity must always be present."""
    assert STYLE_SUFFIX
    assert "flat oil painting" in STYLE_SUFFIX


# ========== Breadcrumb digest ==========


def test_service_passes_breadcrumb_digest_to_visualizer():
    visualizer = FakeVisualizer()
    service = _make_service(visualizer=visualizer)
    service.generate_candidates(
        theme_body="On attention",
        tag_names=[],
        breadcrumb_bodies=["First note.", "Second, later note."],
    )
    digest = visualizer.digests[0]
    assert "First note." in digest
    assert "Second, later note." in digest


def test_service_sends_empty_digest_when_no_breadcrumbs():
    visualizer = FakeVisualizer()
    service = _make_service(visualizer=visualizer)
    service.generate_candidates(theme_body="x", tag_names=[])
    assert visualizer.digests == [""]


def test_digest_empty_for_no_bodies():
    assert build_breadcrumb_digest([]) == ""


def test_digest_empty_for_blank_bodies():
    assert build_breadcrumb_digest(["", "   ", "\n"]) == ""


def test_digest_includes_each_crumb_in_order():
    digest = build_breadcrumb_digest(["alpha", "beta", "gamma"])
    assert digest == "- alpha\n- beta\n- gamma"
    # arc preserved: oldest first, most recent last
    assert digest.index("alpha") < digest.index("beta") < digest.index("gamma")


def test_digest_truncates_long_crumb_to_per_crumb_cap():
    long_body = "x" * 500
    digest = build_breadcrumb_digest([long_body], per_crumb_chars=150)
    # "- " prefix + 150 chars + ellipsis
    assert len(digest) == len("- ") + 150 + len("…")
    assert digest.endswith("…")


def test_digest_caps_total_and_keeps_most_recent():
    # 20 crumbs of ~150 chars each would be ~3000 chars; cap is 1500.
    bodies = [f"crumb{i} " + ("y" * 140) for i in range(20)]
    digest = build_breadcrumb_digest(bodies, per_crumb_chars=150, total_chars=1500)
    assert len(digest) <= 1500 + 40  # small slack for bullet prefixes
    # the most recent crumb must survive; the oldest must be dropped
    assert "crumb19" in digest
    assert "crumb0 " not in digest


def test_digest_always_keeps_at_least_the_most_recent():
    # A single crumb longer than the total budget still yields the most recent.
    digest = build_breadcrumb_digest(["z" * 5000], per_crumb_chars=150, total_chars=100)
    assert digest.startswith("- ")
    assert "z" in digest


def test_digest_strips_markdown_image_syntax():
    digest = build_breadcrumb_digest(["Look ![alt](https://cdn/x.png) at this"])
    assert "https://cdn/x.png" not in digest
    assert "![" not in digest
    assert "Look" in digest and "at this" in digest


def test_digest_keeps_link_text_drops_url():
    digest = build_breadcrumb_digest(["See [the paper](https://arxiv.org/abs/1)"])
    assert "the paper" in digest
    assert "arxiv.org" not in digest


def test_digest_strips_bare_urls():
    digest = build_breadcrumb_digest(["ref https://example.com/foo done"])
    assert "example.com" not in digest
    assert "ref" in digest and "done" in digest


# ========== ClaudeVisualizer ==========


def _fake_anthropic_response(text: str):
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_claude_visualizer_returns_scene_text():
    client = MagicMock()
    client.messages.create.return_value = _fake_anthropic_response(
        "A single robot standing in an empty room."
    )
    visualizer = ClaudeVisualizer(client)

    scene = visualizer.describe_scene("On AI agents", ["ai", "agents"])

    assert scene == "A single robot standing in an empty room."


def test_claude_visualizer_sends_theme_and_tags_in_user_message():
    client = MagicMock()
    client.messages.create.return_value = _fake_anthropic_response("x")
    visualizer = ClaudeVisualizer(client)

    visualizer.describe_scene("On AI agents", ["ai", "agents"])

    kwargs = client.messages.create.call_args.kwargs
    user_msg = kwargs["messages"][0]["content"]
    assert "On AI agents" in user_msg
    assert "Tags: ai, agents" in user_msg


def test_claude_visualizer_includes_digest_when_present():
    client = MagicMock()
    client.messages.create.return_value = _fake_anthropic_response("x")
    visualizer = ClaudeVisualizer(client)

    visualizer.describe_scene("Theme seed", ["t"], "- crumb one\n- crumb two")

    user_msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "develops through these notes" in user_msg
    assert "crumb one" in user_msg
    assert "crumb two" in user_msg


def test_claude_visualizer_omits_digest_block_when_empty():
    client = MagicMock()
    client.messages.create.return_value = _fake_anthropic_response("x")
    visualizer = ClaudeVisualizer(client)

    visualizer.describe_scene("Theme seed", ["t"], "")

    user_msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "develops through these notes" not in user_msg


def test_claude_visualizer_handles_empty_tags():
    client = MagicMock()
    client.messages.create.return_value = _fake_anthropic_response("x")
    visualizer = ClaudeVisualizer(client)

    visualizer.describe_scene("theme", [])

    user_msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "(none)" in user_msg


def test_claude_visualizer_wraps_api_errors():
    import anthropic
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIError(
        message="boom", request=MagicMock(), body=None
    )
    visualizer = ClaudeVisualizer(client)

    with pytest.raises(ImageGenerationError, match="Visualizer error"):
        visualizer.describe_scene("x", [])


def test_claude_visualizer_rejects_empty_response():
    client = MagicMock()
    response = MagicMock()
    response.content = []
    client.messages.create.return_value = response
    visualizer = ClaudeVisualizer(client)

    with pytest.raises(ImageGenerationError, match="empty response"):
        visualizer.describe_scene("x", [])


def test_claude_visualizer_rejects_whitespace_only_response():
    client = MagicMock()
    client.messages.create.return_value = _fake_anthropic_response("   ")
    visualizer = ClaudeVisualizer(client)

    with pytest.raises(ImageGenerationError, match="empty scene"):
        visualizer.describe_scene("x", [])


# ========== ReplicateImageGenerator ==========
#
# These drive a scripted Replicate API through httpx.MockTransport rather than
# stubbing our own call site. That matters: the bug this class was rewritten to fix
# lived in the SDK's control flow (an unbounded poll loop reached only after a
# long-poll expired), and a fake that raises instantly can never reproduce it.


def _pred_json(pid: str, status: str, output=None, error=None) -> dict:
    return {
        "id": pid,
        "model": "black-forest-labs/flux-schnell-lora",
        "version": "v1",
        "status": status,
        "input": {"prompt": "x"},
        "output": output,
        "error": error,
        "logs": "",
        "created_at": "2026-07-21T00:00:00Z",
        "urls": {
            "get": f"https://api.replicate.com/v1/predictions/{pid}",
            "cancel": f"https://api.replicate.com/v1/predictions/{pid}/cancel",
        },
    }


class FakePool:
    """A scripted Replicate API.

    Each ``create`` consumes the next plan (the last plan repeats). A plan is either
    an int HTTP status to fail the create with, or a dict of
    ``{"statuses": [...], "output": [...]}`` where successive polls walk the status
    list and the final entry repeats forever (that is how a wedged pool is modeled).
    """

    def __init__(self, *plans):
        self.plans = list(plans) or [{"statuses": ["succeeded"], "output": ["https://r/x.webp"]}]
        self.creates = 0
        self.polls = 0
        self.cancels: List[str] = []
        self.bodies: List[dict] = []
        self.headers: List[dict] = []
        self.models: List[str] = []
        self._live: dict = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/cancel"):
            pid = path.split("/")[-2]
            self.cancels.append(pid)
            return httpx.Response(200, json=_pred_json(pid, "canceled"))
        if request.method == "POST":
            return self._create(request)
        if request.method == "GET":
            self.polls += 1
            return self._get(path.rsplit("/", 1)[-1])
        return httpx.Response(405, json={"detail": f"unexpected {request.method}"})

    def _create(self, request: httpx.Request) -> httpx.Response:
        import json as _json
        self.bodies.append(_json.loads(request.content or b"{}"))
        self.headers.append(dict(request.headers))
        # /v1/models/{owner}/{name}/predictions
        self.models.append(
            request.url.path.removeprefix("/v1/models/").removesuffix("/predictions")
        )
        plan = self.plans[min(self.creates, len(self.plans) - 1)]
        self.creates += 1
        if isinstance(plan, int):
            return httpx.Response(plan, json={"detail": "scripted failure"})
        pid = f"p{self.creates}"
        self._live[pid] = {
            "statuses": list(plan["statuses"]),
            "output": plan.get("output"),
        }
        return httpx.Response(201, json=self._render(pid))

    def _advance(self, pid: str) -> str:
        statuses = self._live[pid]["statuses"]
        return statuses.pop(0) if len(statuses) > 1 else statuses[0]

    def _render(self, pid: str) -> dict:
        status = self._advance(pid)
        output = self._live[pid]["output"] if status == "succeeded" else None
        return _pred_json(pid, status, output)

    def _get(self, pid: str) -> httpx.Response:
        return httpx.Response(200, json=self._render(pid))


def _generator(pool: "FakePool", **kwargs) -> ReplicateImageGenerator:
    import replicate
    client = replicate.Client(
        api_token="fake", transport=httpx.MockTransport(pool.handler)
    )
    client.poll_interval = 0.01
    kwargs.setdefault("num_outputs", 1)
    kwargs.setdefault("starting_timeout_seconds", 0.2)
    kwargs.setdefault("attempt_timeout_seconds", 0.4)
    kwargs.setdefault("http_read_timeout_seconds", 0.3)
    return ReplicateImageGenerator(client=client, **kwargs)


SUCCESS = {"statuses": ["succeeded"], "output": ["https://r/ok.webp"]}
WEDGED = {"statuses": ["starting"]}  # never leaves "starting" — the real failure mode
# Reaches a GPU and renders, just not instantly. Must NOT be killed as wedged.
SLOW_BUT_ALIVE = {
    "statuses": ["starting", "processing", "processing", "processing", "succeeded"],
    "output": ["https://r/slow.webp"],
}


def test_replicate_generator_missing_token(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    generator = ReplicateImageGenerator()
    with pytest.raises(ImageGenerationError, match="REPLICATE_API_TOKEN"):
        generator.generate("prompt")


def test_wedged_prediction_is_cancelled_and_retried():
    """THE regression test.

    A pool that accepts predictions but never starts them is the documented failure
    mode. Previously replicate.run() would block in an unbounded poll loop here, so
    the retry never fired and the abandoned prediction kept billing. Now: two
    creates (the retry ran) and two cancels (neither orphan was left running).
    """
    pool = FakePool(WEDGED, WEDGED)
    generator = _generator(pool, max_attempts=2)

    with pytest.raises(ImageGenerationError, match="All 1 candidates failed"):
        generator.generate("prompt")

    assert pool.creates == 2, "retry did not fire against a wedged pool"
    assert len(pool.cancels) == 2, "abandoned predictions were left billing"


def test_wedged_first_attempt_then_healthy_worker_succeeds():
    """The whole point of retrying: re-roll off a stuck worker onto a good one."""
    pool = FakePool(WEDGED, SUCCESS)
    generator = _generator(pool, max_attempts=2)

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.creates == 2
    assert pool.cancels == ["p1"]


def test_wedged_pool_fails_over_to_the_next_model():
    """A wedged pool stops scheduling everything, so retrying it is pointless.

    Observed 2026-07-21: flux-schnell-lora stuck in "starting" past 45s while the
    canonical pool succeeded in 25s. In 2026-05 the positions were reversed. The
    retry must change pools, not just re-roll.
    """
    pool = FakePool(WEDGED, SUCCESS)
    generator = _generator(
        pool,
        models=["pool-a/model", "pool-b/model"],
        max_attempts=2,
    )

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.models == ["pool-a/model", "pool-b/model"], "retry reused the bad pool"


def test_slow_but_processing_prediction_is_not_killed_as_wedged():
    """"Queued forever" and "slow" are different failures.

    A healthy cold start was measured at 25s. Treating that as wedged would cancel
    work about to succeed, and still bill for it.
    """
    pool = FakePool(SLOW_BUT_ALIVE)
    generator = _generator(
        pool,
        starting_timeout_seconds=0.05,  # would fire immediately if status were ignored
        attempt_timeout_seconds=5.0,
        max_attempts=1,
    )

    assert generator.generate("prompt") == ["https://r/slow.webp"]
    assert pool.cancels == [], "cancelled a prediction that was actively processing"


def test_wedged_batch_stays_within_the_wall_clock_backstop():
    pool = FakePool(WEDGED)
    generator = _generator(
        pool, num_outputs=4, max_attempts=2, attempt_timeout_seconds=0.2
    )
    started = time.monotonic()
    with pytest.raises(ImageGenerationError):
        generator.generate("prompt")
    elapsed = time.monotonic() - started
    assert elapsed < generator._timeout_seconds + 1.0


@pytest.mark.parametrize("status", [400, 401, 402, 403, 422, 429])
def test_account_level_errors_are_not_retried(status):
    """Retrying a bad token, exhausted credit, or bad input cannot succeed.

    These are identical on every model, so failing over cannot help. It only
    doubles the doomed calls (4 candidates x 2 attempts = 8) and doubles
    time-to-error. 429 is included deliberately: Replicate's documented throttle
    below $5 credit needs a top-up, not another request.
    """
    pool = FakePool(status)
    generator = _generator(pool, max_attempts=2)

    with pytest.raises(ImageGenerationError):
        generator.generate("prompt")

    assert pool.creates == 1, f"HTTP {status} should not be retried"


@pytest.mark.parametrize("status", [404, 500, 502, 503])
def test_model_and_infrastructure_errors_fail_over(status):
    """404 belongs here, not with the permanent errors.

    Observed live 2026-07-21: Replicate returned "No adapter found for model" for a
    model that had succeeded minutes earlier. In a failover list a 404 means "this
    pool is unreachable", which is precisely when the next one should be tried.
    """
    pool = FakePool(status, SUCCESS)
    generator = _generator(pool, max_attempts=2)

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.creates == 2


def test_failed_prediction_is_retried_on_a_new_worker():
    """A "failed" status is the CUDA-OOM shape; a re-roll usually lands healthy."""
    pool = FakePool({"statuses": ["failed"]}, SUCCESS)
    generator = _generator(pool, max_attempts=2)

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.creates == 2


def test_succeeded_with_null_output_is_a_clean_error_not_a_crash():
    """Guards a 500. A prediction can report success with output=None; list(None)
    would raise TypeError, which api.py does not catch."""
    pool = FakePool({"statuses": ["succeeded"], "output": None})
    generator = _generator(pool, max_attempts=1)

    with pytest.raises(ImageGenerationError, match="no output"):
        generator.generate("prompt")


def test_generator_fans_out_one_prediction_per_candidate():
    pool = FakePool(SUCCESS)
    generator = _generator(pool, num_outputs=4)

    urls = generator.generate("a scene")

    assert len(urls) == 4
    assert pool.creates == 4


def test_generator_sends_correct_input_shape_and_does_not_block_on_create():
    pool = FakePool(SUCCESS)
    generator = _generator(pool)

    generator.generate("a scene")

    body = pool.bodies[0]
    assert body["input"]["prompt"] == "a scene"
    assert body["input"]["num_outputs"] == 1
    assert body["input"]["aspect_ratio"] == "1:1"
    assert body["input"]["output_format"] == "webp"
    # wait=False must not become a long-poll: we own the polling now.
    assert "Prefer" not in pool.headers[0]


def test_generator_returns_partial_results_when_some_candidates_fail():
    """Degraded beats dead: one bad candidate must not fail the whole batch."""
    pool = FakePool(SUCCESS, 422, SUCCESS, SUCCESS)
    generator = _generator(pool, num_outputs=4, max_attempts=1)

    assert len(generator.generate("prompt")) == 3


def test_generator_handles_fileoutput_style_objects():
    class _FileOutput:
        url = "https://r/from-object.webp"

    assert ReplicateImageGenerator._extract_url([_FileOutput()]) == "https://r/from-object.webp"


def test_batch_timeout_is_shared_not_per_candidate():
    """Candidates run concurrently, so the budget is batch-wide. Per-future
    timeouts would let a wedged pool burn num_outputs * timeout.

    max_attempts=1 and a modest attempt timeout keep the abandoned worker threads
    short-lived: they cannot be cancelled, and ThreadPoolExecutor joins them at
    interpreter exit, so an over-long attempt here would add invisible wall clock
    to every CI run without showing up in pytest's own timings.
    """
    pool = FakePool(WEDGED)
    generator = _generator(
        pool,
        num_outputs=4,
        timeout_seconds=0.3,
        attempt_timeout_seconds=1.5,
        max_attempts=1,
    )
    started = time.monotonic()
    with pytest.raises(ImageGenerationError, match="All 4 candidates failed"):
        generator.generate("prompt")
    elapsed = time.monotonic() - started
    assert elapsed < 2.0, f"batch took {elapsed:.1f}s — timeout is not shared"


def test_backstop_is_derived_to_fit_the_full_retry_budget():
    """Worst realistic path: N-1 attempts bail early as wedged, the last runs full."""
    generator = ReplicateImageGenerator(
        starting_timeout_seconds=15,
        attempt_timeout_seconds=40,
        http_read_timeout_seconds=10,
        max_attempts=2,
    )
    assert generator._timeout_seconds == 15 + 40 + 20


def test_explicit_timeout_overrides_the_derived_backstop():
    generator = ReplicateImageGenerator(timeout_seconds=3.0, max_attempts=2)
    assert generator._timeout_seconds == 3.0


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, 20.0),      # unset
        ("", 20.0),        # empty
        ("   ", 20.0),     # whitespace
        ("25s", 20.0),     # malformed: would crash app startup if it raised
        ("0", 20.0),       # zero would disable the bound entirely
        ("-5", 20.0),      # negative is nonsense
        ("30", 30.0),      # valid
    ],
)
def test_env_number_rejects_values_that_would_disable_the_bound(monkeypatch, raw, expected):
    from app.images.providers import _env_number

    if raw is None:
        monkeypatch.delenv("SOME_KNOB", raising=False)
    else:
        monkeypatch.setenv("SOME_KNOB", raw)

    assert _env_number("SOME_KNOB", 20.0, float) == expected


# ========== R2ImageStore ==========


def _fake_http_response(status: int = 200, content: bytes = b"\x89PNG\r\n\x1a\n_data_", ctype: str = "image/png"):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status
    response.content = content
    response.headers = {"content-type": ctype}
    response.raise_for_status = MagicMock()
    if status >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"status {status}", request=MagicMock(), response=response
        )
    return response


@pytest.mark.parametrize(
    "url,allowed",
    [
        ("https://replicate.delivery/x/out.webp", True),
        ("https://pbxt.replicate.delivery/x/y.webp", True),
        ("https://cdn.replicate.delivery/x.webp", True),
        ("http://replicate.delivery/x.webp", False),
        ("https://evil.example.com/x.webp", False),
        ("https://replicate.delivery.evil.com/x.webp", False),
        ("file:///etc/passwd", False),
        ("https://localhost/x.webp", False),
    ],
)
def test_r2_store_host_allowlist(url, allowed):
    fetch = MagicMock(return_value=_fake_http_response())
    put = MagicMock(return_value="https://cdn.example/saved.png")
    store = R2ImageStore(fetch=fetch, put=put)

    if allowed:
        assert store.commit(url) == "https://cdn.example/saved.png"
    else:
        with pytest.raises(ImageCommitError, match="allowlist"):
            store.commit(url)


def test_r2_store_passes_through_to_put_with_generated_key():
    fetch = MagicMock(return_value=_fake_http_response())
    put = MagicMock(return_value="https://cdn.example/saved.png")
    store = R2ImageStore(fetch=fetch, put=put)

    store.commit("https://replicate.delivery/x/out.webp")

    args, _ = put.call_args
    key, body, ctype = args
    assert key.startswith("theme-")
    assert key.endswith(".png")
    assert ctype == "image/png"
    assert body.startswith(b"\x89PNG")


def test_r2_store_rejects_unknown_content_type():
    fetch = MagicMock(return_value=_fake_http_response(ctype="text/html"))
    store = R2ImageStore(fetch=fetch, put=MagicMock())
    with pytest.raises(ImageCommitError, match="Unsupported content-type"):
        store.commit("https://replicate.delivery/x/out.webp")


def test_r2_store_rejects_payload_without_magic_bytes():
    fetch = MagicMock(return_value=_fake_http_response(content=b"<html>evil</html>", ctype="image/png"))
    store = R2ImageStore(fetch=fetch, put=MagicMock())
    with pytest.raises(ImageCommitError, match="not a recognized image"):
        store.commit("https://replicate.delivery/x/out.webp")


def test_r2_store_wraps_http_errors():
    fetch = MagicMock(side_effect=httpx.ConnectError("boom"))
    store = R2ImageStore(fetch=fetch, put=MagicMock())
    with pytest.raises(ImageCommitError, match="Could not download"):
        store.commit("https://replicate.delivery/x/out.webp")


def test_r2_store_does_not_follow_redirects():
    """Defense against allowlisted hosts 302'ing to private IPs."""
    fetch = MagicMock(return_value=_fake_http_response())
    store = R2ImageStore(fetch=fetch, put=MagicMock(return_value="x"))
    store.commit("https://replicate.delivery/x/out.webp")
    assert fetch.call_args.kwargs["follow_redirects"] is False


def test_r2_store_accepts_content_type_with_charset():
    fetch = MagicMock(return_value=_fake_http_response(ctype="image/png; charset=binary"))
    store = R2ImageStore(fetch=fetch, put=MagicMock(return_value="x"))
    assert store.commit("https://replicate.delivery/x/out.webp") == "x"
