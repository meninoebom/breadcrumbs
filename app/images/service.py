"""ThemeImageService orchestrates theme → scene → candidates → commit.

Protocols here describe what the service needs; concrete implementations live
in app.images.providers. Injecting dependencies keeps this module free of I/O
and trivially testable with fakes.
"""

import re
from dataclasses import dataclass
from typing import List, Protocol, Sequence


# Markdown image syntax, inline links, and bare URLs are noise to the visualizer
# (and can blow the character budget), so they're scrubbed from the digest.
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL_RE = re.compile(r"https?://\S+")

DIGEST_PER_CRUMB_CHARS = 150
DIGEST_TOTAL_CHARS = 1500


def _clean_body(body: str) -> str:
    """Strip image markdown and URLs, keep link text, collapse whitespace."""
    text = _IMAGE_RE.sub("", body)
    text = _LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    return " ".join(text.split())


def build_breadcrumb_digest(
    bodies: Sequence[str],
    *,
    per_crumb_chars: int = DIGEST_PER_CRUMB_CHARS,
    total_chars: int = DIGEST_TOTAL_CHARS,
) -> str:
    """Condense breadcrumb bodies into a bounded, arc-preserving digest.

    ``bodies`` is expected in chronological order (oldest first). Each crumb is
    cleaned of markdown images/URLs and truncated to ``per_crumb_chars``. When
    the combined text exceeds ``total_chars`` the oldest crumbs are dropped so
    the most recent development survives, and the kept crumbs stay in
    chronological order (most recent last) so the model reads the arc.
    Returns "" when there is no usable content.
    """
    snippets: List[str] = []
    for body in bodies:
        cleaned = _clean_body(body)
        if not cleaned:
            continue
        if len(cleaned) > per_crumb_chars:
            cleaned = cleaned[:per_crumb_chars].rstrip() + "…"
        snippets.append(cleaned)

    if not snippets:
        return ""

    # Walk newest → oldest, keeping crumbs until the budget is spent, always
    # retaining at least the most recent one.
    selected: List[str] = []
    running = 0
    for snippet in reversed(snippets):
        addition = len(snippet) + (1 if selected else 0)  # +1 for the newline joiner
        if selected and running + addition > total_chars:
            break
        selected.append(snippet)
        running += addition
    selected.reverse()

    return "\n".join(f"- {s}" for s in selected)


STYLE_SUFFIX = (
    "Rendered as a flat oil painting in a limited three-color palette, "
    "figurative and confident, contemporary museum-quality painting, "
    "tone balanced between gravity and play. "
    "Render any human figure exactly as the scene describes; do not default to a "
    "white or male or young or thin figure when the scene calls for someone "
    "different. "
    "When hands are visible, they rest calmly at the sides, are folded, or hold "
    "a single object — never reaching, gesturing, or pointing."
)


@dataclass(frozen=True)
class GenerationResult:
    prompt: str
    candidates: List[str]


class Visualizer(Protocol):
    """Translates abstract theme writing into a concrete, renderable scene sentence."""

    def describe_scene(
        self,
        theme_body: str,
        tag_names: Sequence[str],
        breadcrumb_digest: str = "",
    ) -> str: ...


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
        breadcrumb_bodies: Sequence[str] = (),
    ) -> GenerationResult:
        digest = build_breadcrumb_digest(breadcrumb_bodies)
        scene = self._visualizer.describe_scene(theme_body, tag_names, digest)
        prompt = compose_prompt(scene, self._style_suffix)
        candidates = self._generator.generate(prompt)
        return GenerationResult(prompt=prompt, candidates=candidates)

    def commit_candidate(self, source_url: str) -> str:
        return self._store.commit(source_url)
