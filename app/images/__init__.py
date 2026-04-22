"""Theme cover image generation package.

Public API:
- ThemeImageService: the orchestrator, injected via Depends in the API layer.
- default_theme_image_service(): production wiring (Claude + Replicate + R2).
- ImageGenerationError, ImageCommitError: raised by the service; the API layer maps to HTTP status.
- STYLE_SUFFIX: visual identity for crumb.blog; applied to every generated prompt.
"""

import os
from functools import lru_cache

import anthropic
from dotenv import load_dotenv

from app.images.errors import ImageCommitError, ImageGenerationError
from app.images.providers import (
    ClaudeVisualizer,
    R2ImageStore,
    ReplicateImageGenerator,
)
from app.images.service import (
    STYLE_SUFFIX,
    GenerationResult,
    ImageGenerator,
    ImageStore,
    ThemeImageService,
    Visualizer,
    compose_prompt,
)

load_dotenv()


@lru_cache
def default_theme_image_service() -> ThemeImageService:
    """Production wiring. Cached per-process; all providers are stateless-ish."""
    return ThemeImageService(
        visualizer=ClaudeVisualizer(anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))),
        generator=ReplicateImageGenerator(),
        store=R2ImageStore(),
    )


__all__ = [
    "GenerationResult",
    "ImageCommitError",
    "ImageGenerationError",
    "ImageGenerator",
    "ImageStore",
    "STYLE_SUFFIX",
    "ThemeImageService",
    "Visualizer",
    "compose_prompt",
    "default_theme_image_service",
]
