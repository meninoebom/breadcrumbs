"""Tests for app.images — service orchestration and provider internals.

Three layers, each tested in isolation:
- service.py: orchestration only, via fakes for all three protocols
- providers.py: concrete providers with their external clients mocked
- __init__.py: the factory wires prod deps; covered by endpoint tests
"""

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

    def describe_scene(self, theme_body: str, tag_names: Sequence[str]) -> str:
        self.calls.append((theme_body, tuple(tag_names)))
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
        def describe_scene(self, body, tags):
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


def test_replicate_generator_missing_token(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    generator = ReplicateImageGenerator()
    with pytest.raises(ImageGenerationError, match="REPLICATE_API_TOKEN"):
        generator.generate("prompt")


def test_replicate_generator_fans_out_one_call_per_candidate(monkeypatch):
    """Each candidate is its own prediction with num_outputs=1 — avoids GPU OOM."""
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")
    counter = {"n": 0}

    def fake_runner(model, input):
        counter["n"] += 1
        return [f"https://r/{counter['n']}.webp"]

    generator = ReplicateImageGenerator(runner=fake_runner, num_outputs=4)
    urls = generator.generate("a scene")

    assert len(urls) == 4
    assert counter["n"] == 4
    assert set(urls) == {f"https://r/{i}.webp" for i in range(1, 5)}


def test_replicate_generator_sends_correct_input_shape(monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")
    fake_runner = MagicMock(return_value=["https://r/1.webp"])
    generator = ReplicateImageGenerator(runner=fake_runner, num_outputs=1)

    generator.generate("a scene")

    call_input = fake_runner.call_args.kwargs["input"]
    assert call_input["prompt"] == "a scene"
    assert call_input["num_outputs"] == 1
    assert call_input["aspect_ratio"] == "1:1"
    assert call_input["output_format"] == "webp"


def test_replicate_generator_handles_fileoutput_objects(monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")
    item = MagicMock()
    item.url = "https://r/1.webp"
    fake_runner = MagicMock(return_value=[item])
    generator = ReplicateImageGenerator(runner=fake_runner, num_outputs=1)

    assert generator.generate("prompt") == ["https://r/1.webp"]


def test_replicate_generator_returns_partial_results_when_some_calls_fail(monkeypatch):
    """One bad candidate shouldn't fail the whole batch — degraded is better than dead."""
    import replicate.exceptions
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")
    counter = {"n": 0}

    def flaky_runner(model, input):
        counter["n"] += 1
        if counter["n"] == 2:
            raise replicate.exceptions.ReplicateError("CUDA OOM on this one")
        return [f"https://r/{counter['n']}.webp"]

    generator = ReplicateImageGenerator(runner=flaky_runner, num_outputs=4)
    urls = generator.generate("prompt")
    assert len(urls) == 3


def test_replicate_generator_raises_when_all_calls_fail(monkeypatch):
    import replicate.exceptions
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")
    broken = MagicMock(side_effect=replicate.exceptions.ReplicateError("upstream 502"))
    generator = ReplicateImageGenerator(runner=broken, num_outputs=4)
    with pytest.raises(ImageGenerationError, match="All 4 candidates failed"):
        generator.generate("prompt")


def test_replicate_generator_times_out_stuck_predictions(monkeypatch):
    """A wedged Replicate prediction must not hang the request forever."""
    import time
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")

    def slow_runner(model, input):
        time.sleep(5)  # would hang forever in the real failure mode
        return ["never seen"]

    generator = ReplicateImageGenerator(
        runner=slow_runner, num_outputs=2, timeout_seconds=0.1
    )
    with pytest.raises(ImageGenerationError, match="timed out"):
        generator.generate("prompt")


def test_replicate_generator_wraps_http_errors(monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake")
    broken = MagicMock(side_effect=httpx.ConnectError("timeout"))
    generator = ReplicateImageGenerator(runner=broken, num_outputs=1)
    with pytest.raises(ImageGenerationError, match="Network error"):
        generator.generate("prompt")


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
