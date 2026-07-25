# Theme Cover Images

AI-generated cover images per theme. Claude translates the theme's text into a concrete scene description, Flux Schnell renders the scene. Writer picks from a grid of 4 candidates; the chosen image is re-uploaded to R2 for stable hosting.

## Pipeline

```
theme.body_md + tags
        │
        ▼
  ClaudeVisualizer.describe_scene()        (app/images/providers.py)
        │  → one-sentence concrete scene
        ▼
  compose_prompt(scene, STYLE_SUFFIX)       (app/images/service.py)
        │  → full Flux prompt
        ▼
  ReplicateImageGenerator.generate()        (app/images/providers.py)
        │  → 4 candidate URLs (Replicate temp links, expire in ~1h)
        ▼
  writer picks one
        │
        ▼
  R2ImageStore.commit()                     (app/images/providers.py)
        │  → validates host allowlist + magic bytes
        │  → uploads bytes to R2
        │  → returns permanent URL
        ▼
  theme.image_url persisted
```

## Why the two-step pipeline

Image models like Flux can't render meta-language. If a theme is "The way we talk about AI agents is wrong," passing that verbatim gives Flux nothing visual to latch onto, and it falls back to generic "contemporary painting" defaults. Claude is good at the translation step — abstract text → concrete scene — which is where the added LLM call earns its keep. Concrete scene → image is Flux's sweet spot.

## Module layout

```
app/images/
├── __init__.py      # public API + default_theme_image_service() factory
├── errors.py        # ImageGenerationError, ImageCommitError
├── service.py       # Protocols (Visualizer, ImageGenerator, ImageStore),
│                    # ThemeImageService, compose_prompt, STYLE_SUFFIX
└── providers.py     # ClaudeVisualizer, ReplicateImageGenerator, R2ImageStore
```

- **`service.py` has no I/O.** It composes prompts and calls protocol methods. Tests use fake providers.
- **`providers.py` wraps vendor SDKs** and translates vendor-specific errors into `ImageGenerationError` / `ImageCommitError` so the service and API layers never import `anthropic` or `replicate`.
- **Providers accept their clients/callables as constructor args** (`client`, `runner`, `fetch`, `put`). Tests pass doubles directly — no monkeypatching module globals.
- **API layer uses FastAPI `Depends(default_theme_image_service)`**. Tests override via `app.dependency_overrides`.

## Where to tune taste

All taste decisions live in two places:

| Knob | File | What it shapes |
|---|---|---|
| `VISUALIZER_SYSTEM_PROMPT` | `app/images/providers.py` | How Claude translates themes into scenes. The biggest lever — controls concreteness, scene composition, metaphor preference. |
| `STYLE_SUFFIX` | `app/images/service.py` | Visual identity: medium, palette, tone. Appended to every Flux prompt. |

Flux prompts want **natural-language prose, not comma-tag soup**. Describe the scene like a photo caption. Include one or two style qualifiers, not a pile of adjectives.

## API endpoints

- `POST /api/themes/{id}/generate-image` — admin-only; runs the pipeline up to `compose_prompt + generate`, returns `{prompt, candidates: string[]}`. Does not write to the DB.
- `POST /api/themes/{id}/image` — admin-only; body `{source_url}`; validates URL against Replicate host allowlist, downloads, uploads to R2, saves `theme.image_url`.
- `DELETE /api/themes/{id}/image` — admin-only; clears `theme.image_url`. (Not routable through `PUT /api/themes/{id}` — `image_url` is explicitly excluded from `THEME_UPDATABLE_FIELDS` to prevent arbitrary URL injection.)

## SSRF defenses on `commit`

The commit endpoint accepts a source URL from the client and fetches it server-side — a classic SSRF hazard if unguarded. The `R2ImageStore` applies:

1. **HTTPS only** (no `http://` or `file://`)
2. **Host allowlist**: `replicate.delivery` and `pbxt.replicate.delivery` (plus any subdomain)
3. **No redirect following** (`follow_redirects=False`) — stops allowlisted hosts from 302'ing to internal IPs
4. **Content-type allowlist**: `image/webp`, `image/png`, `image/jpeg` only
5. **Magic-byte validation** on the downloaded payload — HTML error pages or JSON responses are rejected even if the content-type header lies

## Required env vars

| Var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude visualizer |
| `REPLICATE_API_TOKEN` | Flux image generation |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` | Storage — enforced by `app/storage.py:assert_r2_env()` |

A missing R2 var returns a clean 500 "Storage is misconfigured"; without this guard the code would previously persist a relative URL like `/theme-xxx.webp` into the DB. See `app/storage.py`.

## Cost + latency

Per generation (click on the Generate button):

- Claude Haiku 4.5: ~$0.0005 (~200 input tokens + ~60 output tokens)
- Flux Schnell grid-of-4: ~$0.012
- **Total: ~$0.0125, ~6–10 seconds**

Iteration is cheap. Budget 20–50 generations while tuning the visualizer prompt or style suffix.

## Extending

**Swap providers**: write a new class that conforms to the `Visualizer`, `ImageGenerator`, or `ImageStore` protocol in `service.py`. Wire it into `default_theme_image_service()` in `__init__.py`. Nothing else changes.

**Add a test**: fakes live at the top of `tests/test_images.py` — `FakeVisualizer`, `FakeImageGenerator`, `FakeImageStore`. Use them directly with `ThemeImageService` for service-level tests; for endpoint tests, the `fake_image_service` fixture in `tests/test_api_themes.py` overrides `default_theme_image_service` via `app.dependency_overrides`.

## Gotchas

- **Flux `go_fast=true` (default) breaks seed determinism.** If you try to tune by freezing a seed, outputs still vary. The grid-of-4 UX doesn't need determinism — just fresh options each click.
- **Replicate temp URLs expire in ~1 hour.** Don't persist them. Always commit via the `/image` endpoint to get a stable R2 URL.
- **`from __future__ import annotations` + SQLModel** — standard project gotcha applies here too; don't add it to `app/images/*`.
