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
    kwargs.setdefault("timeout_seconds", 0.3)
    return ReplicateImageGenerator(client=client, **kwargs)


SUCCESS = {"statuses": ["succeeded"], "output": ["https://r/ok.webp"]}
WEDGED = {"statuses": ["starting"]}  # never leaves "starting" — the real failure mode
# Sits in "starting" for several polls before it renders. The old two-tier design
# killed this at the 15s "starting" bound; one generous deadline must let it finish.
SLOW_TO_SCHEDULE = {
    "statuses": ["starting", "starting", "starting", "processing", "succeeded"],
    "output": ["https://r/slow.webp"],
}


def test_replicate_generator_missing_token(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    generator = ReplicateImageGenerator()
    with pytest.raises(ImageGenerationError, match="REPLICATE_API_TOKEN"):
        generator.generate("prompt")


def test_wedged_prediction_is_cancelled_and_failed_over():
    """THE regression test.

    A pool that accepts predictions but never starts them is the documented failure
    mode. replicate.run() would block here in an unbounded poll loop; we bound it,
    cancel the abandoned prediction so it stops billing, and fail over to the other
    pool. Both default pools wedge here: two creates, two cancels, one clean error.
    """
    pool = FakePool(WEDGED, WEDGED)
    generator = _generator(pool)

    with pytest.raises(ImageGenerationError, match="All 1 candidates failed"):
        generator.generate("prompt")

    assert pool.creates == 2, "did not fail over to the second pool"
    assert len(pool.cancels) == 2, "abandoned predictions were left billing"


def test_wedged_first_pool_then_healthy_second_pool_succeeds():
    """Failover's whole point: a wedged pool must not sink the candidate."""
    pool = FakePool(WEDGED, SUCCESS)
    generator = _generator(pool)

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.creates == 2
    assert pool.cancels == ["p1"]


def test_wedged_pool_fails_over_to_the_next_model():
    """A wedged pool stops scheduling everything, so the retry must change pools.

    Observed 2026-07: flux-schnell-lora stuck in "starting" past 45s while the
    canonical pool succeeded in seconds. Failover moves to the next pool; it does not
    re-roll the wedged one.
    """
    pool = FakePool(WEDGED, SUCCESS)
    generator = _generator(pool, models=["pool-a/model", "pool-b/model"])

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.models == ["pool-a/model", "pool-b/model"], "retry reused the bad pool"


def test_slow_to_schedule_prediction_is_not_killed():
    """The regression #94 introduced: a healthy cold start sits in "starting" for
    15-30s. The old 15s "starting" bound cancelled it and failed over for no reason;
    one generous deadline lets it finish. Here it stays "starting" for three polls
    before it renders."""
    pool = FakePool(SLOW_TO_SCHEDULE)
    generator = _generator(pool, timeout_seconds=5.0)

    assert generator.generate("prompt") == ["https://r/slow.webp"]
    assert pool.cancels == [], "cancelled a prediction that was still scheduling"


@pytest.mark.parametrize("status", [400, 401, 402, 403, 422, 429])
def test_account_level_create_errors_are_not_retried_or_failed_over(status):
    """A bad token, exhausted credit, bad input, or rate limit is identical on every
    pool, so retrying the same pool or failing over only doubles doomed calls. 402 is
    the out-of-credit signal (top up); 429 the documented sub-$5 throttle."""
    pool = FakePool(status)
    generator = _generator(pool)

    with pytest.raises(ImageGenerationError):
        generator.generate("prompt")

    assert pool.creates == 1, f"HTTP {status} should not be retried or failed over"


@pytest.mark.parametrize("status", [404, 500, 502, 503])
def test_transient_create_error_retries_the_same_pool(status):
    """The flux-schnell fix. Replicate returns transient "No adapter found" 404s (and
    5xx) for a pool that works moments later. That is a blip on THIS pool, so we
    re-create on the same pool rather than bouncing to a possibly-dead sibling."""
    pool = FakePool(status, SUCCESS)
    generator = _generator(pool, models=["pool-a/model", "pool-b/model"])

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.creates == 2
    assert pool.models == ["pool-a/model", "pool-a/model"], "did not retry same pool"


def test_create_errors_fail_over_after_exhausting_the_same_pool():
    """Once a pool's create attempts are spent, move on: pool-a 404s both attempts,
    then pool-b succeeds."""
    pool = FakePool(404, 404, SUCCESS)
    generator = _generator(
        pool, models=["pool-a/model", "pool-b/model"], create_attempts=2
    )

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.models == ["pool-a/model", "pool-a/model", "pool-b/model"]


def test_failed_prediction_fails_over_to_the_next_pool():
    """A "failed" status is the CUDA-OOM shape; failing over usually lands healthy."""
    pool = FakePool({"statuses": ["failed"]}, SUCCESS)
    generator = _generator(pool)

    assert generator.generate("prompt") == ["https://r/ok.webp"]
    assert pool.creates == 2


def test_succeeded_with_null_output_is_a_clean_error_not_a_crash():
    """Guards a 500. A prediction can report success with output=None; list(None)
    would raise TypeError, which api.py does not catch."""
    pool = FakePool({"statuses": ["succeeded"], "output": None})
    generator = _generator(pool)

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
    generator = _generator(pool, num_outputs=4)

    assert len(generator.generate("prompt")) == 3


def test_generator_handles_fileoutput_style_objects():
    class _FileOutput:
        url = "https://r/from-object.webp"

    assert ReplicateImageGenerator._extract_url([_FileOutput()]) == "https://r/from-object.webp"


def test_wedged_batch_returns_concurrently_not_summed():
    """Candidates run in parallel and share one deadline. Four wedged candidates,
    each trying two pools, must surface in roughly one candidate's time, not four."""
    pool = FakePool(WEDGED)
    generator = _generator(pool, num_outputs=4, timeout_seconds=0.2)

    started = time.monotonic()
    with pytest.raises(ImageGenerationError, match="All 4 candidates failed"):
        generator.generate("prompt")
    elapsed = time.monotonic() - started

    assert elapsed < 2.0, f"batch took {elapsed:.1f}s — candidates were not concurrent"


def test_batch_timeout_scales_with_pools_and_per_attempt_timeout():
    """A candidate tries each pool once, so the batch backstop is len(models) *
    timeout (plus HTTP slack), never below the per-candidate budget."""
    generator = ReplicateImageGenerator(models=["a/m", "b/m"], timeout_seconds=10.0)
    assert generator._batch_timeout_seconds == 2 * 10.0 + 15.0


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
