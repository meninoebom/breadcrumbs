"""ThemeImageService orchestrates theme → scene → candidates → commit.

Protocols here describe what the service needs; concrete implementations live
in app.images.providers. Injecting dependencies keeps this module free of I/O
and trivially testable with fakes.
"""

from dataclasses import dataclass
from typing import List, Protocol, Sequence


STYLE_SUFFIX = (
    "Rendered as a flat oil painting in a limited three-color palette, "
    "figurative and confident, contemporary museum-quality painting, "
    "tone balanced between gravity and play. "
    "If human figures are included, represent varied skin tones, ages, and body types. "
    "When hands are visible, they rest calmly at the sides, are folded, or hold "
    "a single object — never reaching, gesturing, or pointing."
)


@dataclass(frozen=True)
class GenerationResult:
    prompt: str
    candidates: List[str]


class Visualizer(Protocol):
    """Translates abstract theme writing into a concrete, renderable scene sentence."""

    def describe_scene(self, theme_body: str, tag_names: Sequence[str]) -> str: ...


class ImageGenerator(Protocol):
    """Produces candidate image URLs from a descriptive prompt."""

    def generate(self, prompt: str) -> List[str]: ...


class ImageStore(Protocol):
    """Persists an image referenced by URL and returns a permanent URL."""

    def commit(self, source_url: str) -> str: ...


def compose_prompt(scene: str, style_suffix: str) -> str:
    """Combine a scene description and a style suffix into a final prompt."""
    return f"{scene.strip()} {style_suffix.strip()}"


class ThemeImageService:
    """Orchestrates visualize → generate → commit. All providers injected."""

    def __init__(
        self,
        *,
        visualizer: Visualizer,
        generator: ImageGenerator,
        store: ImageStore,
        style_suffix: str = STYLE_SUFFIX,
    ) -> None:
        self._visualizer = visualizer
        self._generator = generator
        self._store = store
        self._style_suffix = style_suffix

    def generate_candidates(
        self,
        theme_body: str,
        tag_names: Sequence[str],
    ) -> GenerationResult:
        scene = self._visualizer.describe_scene(theme_body, tag_names)
        prompt = compose_prompt(scene, self._style_suffix)
        candidates = self._generator.generate(prompt)
        return GenerationResult(prompt=prompt, candidates=candidates)

    def commit_candidate(self, source_url: str) -> str:
        return self._store.commit(source_url)
