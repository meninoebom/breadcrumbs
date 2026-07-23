# Claude Development Guide

## Project Overview
**Name:** Breadcrumbs
**Description:** A blog of collected breadcrumbs organized into themes. Based on a public Google doc maintained by a Google PM, this app makes it easy to create themes, add small thought atoms (breadcrumbs) to them, tag themes, and read through published content in a continuous stream format.
**Inspiration:** https://docs.google.com/document/d/1GrEFrdF_IzRVXbGH1lG0aQMlvsB71XihPPqQN-ONTuo/edit?tab=t.0

**Tech Stack:**
- **Backend:** Python, FastAPI, PostgreSQL, SQLModel
- **Frontend:** TanStack Router, TanStack Query, Tailwind CSS, Shadcn UI

## Local Dev via mise

breadcrumbs is polyglot (FastAPI backend at root + Vite/React frontend in `frontend/`), so
`mise.toml` pins both toolchains and orchestrates tasks across them. See
`~/projects/knowledge-base/mise.md` for the rationale.

```bash
mise install        # provision node 22, pnpm 10.33, python 3.13, uv
mise run dev        # Vite frontend + FastAPI backend together
mise run check      # eslint + tsc (web) and pytest (api) — the gate
mise run test       # backend pytest only
mise run migrate    # alembic upgrade head
mise run build      # production Vite build
mise tasks ls       # all tasks
```

Notes:
- **Frontend is on pnpm** (version pinned via `packageManager` and `mise.toml [tools]`); backend
  is on uv. `mise` is for local dev only.
- **uv owns the Python venv, not mise** — mise's `python = "3.13"` pin matches `.python-version`,
  but `uv run` reuses an existing `.venv` regardless. `rm -rf .venv && uv sync` rebuilds on 3.13.
- **No ruff wired here yet**, so `check:api` is pytest-only.
- **CI gotcha:** never pipe `mise run check` through `tail` — it masks mise's exit code.

## Production build & deploy

Production is built from a committed multi-stage **`Dockerfile`** (not the local mise
setup, which mise never touches prod). Every tool version is pinned in-repo: Node 22,
pnpm 10.33.0 (installed directly with `npm i -g`, **not** corepack), Python 3.13,
uv 0.8.12. `railway.toml` sets `builder = "dockerfile"`; there is no `nixpacks.toml`.

- **Never reintroduce Nixpacks or corepack here.** The prior Nixpacks build silently
  broke deploys for ~2 months (it defaulted to Node 18, and corepack failed signature
  verification on a rotated npm key). The Dockerfile exists specifically to make the
  build explicit and reproducible. Full postmortem: `docs/solutions/deployment-gotchas.md`.
- **Test build changes locally before pushing:** `docker build -t bc .` then run against
  a throwaway Postgres (SQLite can't run the Postgres-only migrations). The container's
  `CMD` runs `alembic upgrade head` then boots uvicorn; the app serves the built SPA from
  `frontend/dist`.
- **Runtime config lives in Railway**, not the image: `PORT`, `ENVIRONMENT=production`,
  `DATABASE_URL`, `R2_*`, `ANTHROPIC_API_KEY`, `REPLICATE_API_TOKEN`, `JWT_SECRET`,
  `ADMIN_PASSWORD`. Nothing sensitive is baked into the Dockerfile.

## Development Workflow

**Tracking what's next:**
- `docs/roadmap.md` — Phases and milestones (updated when phases complete)
- GitHub Issues — Individual tasks with acceptance criteria (the backlog)
- `CLAUDE.md` (this file) — Conventions, patterns, gotchas (updated when you learn something permanent)

**Other docs:**
- `llms.txt` — Public documentation for LLM discovery
- `docs/log/` — Learning journal entries (post-PR reflections)

**Starting a session:** Run `gh issue list` to see what's next. Read `docs/roadmap.md` for big picture.

## Code Conventions

### Python Backend (FastAPI)
- Use `snake_case` for variables, functions, and file names
- Use `PascalCase` for classes and SQLModel models
- Type hints required for all function signatures
- Format with `black` and `ruff`
- Follow FastAPI best practices for dependency injection
- SQLModel for ORM (combines SQLAlchemy + Pydantic)

**File Structure:**
```
/app
  api.py       - FastAPI routes (all endpoints)
  models.py    - SQLModel database + Pydantic models
  auth.py      - JWT auth, password verification, require_admin dependency
  db.py        - Database engine, session management, dotenv loading
  cli.py       - CLI entry points (uv run dev)
```

### TypeScript Frontend (React)
- Use `PascalCase` for components
- Use `camelCase` for variables and functions
- Prefer function components with hooks
- TanStack Router for file-based routing
- TanStack Query for server state management
- Tailwind CSS for styling
- Shadcn UI for component primitives

**File Structure:**
```
/frontend
  /src
    /routes       - TanStack Router file-based routes
    /components   - Reusable React components
    /lib          - Utilities and helpers
    /hooks        - Custom React hooks
```

**Reusable authoring primitives (reuse, don't rebuild):**
- `hooks/use-draft.ts` — `useDraft(key, { enabled })`: localStorage-backed string
  with debounced persist, restore-on-mount, and `clear()` on save. Remount the
  consumer via a `key` prop when the storage key changes. Backs the breadcrumb
  add form and the new-theme dialog so navigation never eats writing.
- `components/writer/markdown-field.tsx` — `WritePreviewToggle` + `MarkdownPreview`
  (matches the read view's `prose prose-sm`). Keep the textarea mounted (hide via
  `cn(mode === "preview" && "hidden")`) so content, cursor, and the Cmd+Enter
  binding survive the toggle.
- `components/writer/highlight-context.tsx` — `HighlightProvider` / `useHighlight`
  to flag a just-saved breadcrumb across the `BreadcrumbItem` recursion without
  prop-drilling.
- Breadcrumb save binding: **Cmd/Ctrl+Enter saves, plain Enter is a newline** in
  all authoring textareas. Preserve this when adding new ones.

### Architecture Patterns
- **Full-stack separation:** Backend and frontend in separate directories
- **API-first design:** Backend exposes RESTful JSON API
- **Theme-based organization:** Breadcrumbs grouped by theme, themes are tagged and searchable
- **Chronological display:** Themes and their breadcrumbs presented as continuous stream with clear theme boundaries
- **Markdown support:** All content rendered as markdown
- **Draft/publish workflow:** Themes can be drafted and published; readers only see published themes

### Testing Strategy
- **Backend:** pytest for unit and integration tests
- **Frontend:** Vitest + React Testing Library
- **Coverage target:** 70%+ for critical paths
- **E2E:** Playwright for key user flows
- **Testing with SQLite:** Use in-memory (`:memory:`) with StaticPool; SQLite doesn't preserve timezone info on datetime fields

### Git Workflow
- Branch naming: `feature/description` or `fix/description`
- Commit format: `type: description` (feat, fix, docs, refactor, test)
- PRs reviewed via `/pr-review-toolkit:review-pr` before merge

### After Completing Work (Agent Self-Assessment)
Before wrapping up a non-trivial PR, self-assess:
- What was the hardest decision or trickiest problem?
- Did anything surprise you or require a workaround?
- Would a future session benefit from knowing this?
If yes, update this CLAUDE.md with the pattern or gotcha — don't wait to be asked.

### Post-PR Learning Reflection (Brandon's Journal)
After each PR, offer:
> "This might be worth a log entry — want to reflect on it, or skip?"

**Skip-worthy:** Typos, dependency bumps, minor CSS, config changes.
**Log-worthy:** Features, architecture decisions, milestones, workflow learnings.

If yes, create `docs/log/NNN-slug.md` and update the README.md index.
See `docs/log/README.md` for format and dimensions.

## Core Features
- **Theme creation:** Writers create themes as containers for related breadcrumbs
- **Breadcrumb authoring:** Add small individual thought atoms (breadcrumbs) to themes
- **Tag-based organization:** Tags applied at theme level for filtering and discovery
- **Tag usage gradient:** Tags sorted by usage with 5-tier opacity gradient showing relative popularity
- **Tag chip input:** Typeahead suggestions, comma/Enter to commit, visual chips distinguishing existing vs new tags
- **Tag drag-to-reorder:** Authenticated writers drag tags in sidebar (desktop) or mobile pill strip to set custom server-side order; `position` int column on Tag; `PATCH /api/tags/reorder` (auth-required); sort cycles custom → usage → alpha; order persists across devices
- **Draft/publish workflow:** Writers can draft themes before publishing to readers
- **Authenticated editing:** Writers login to see unpublished themes and edit existing ones
- **Easy to read:** Continuous stream presentation with clear theme boundaries (not traditional blog articles)
- **Tag browsing:** Readers browse tags in custom (server-side) order with usage/alpha toggle; filter themes by tag
- **Search:** Full-text search across theme bodies, breadcrumb content, and tags
- **Timestamps:** Every breadcrumb has a timestamp
- **Markdown rendering:** Full markdown support for formatting
- **Mobile responsive:** Horizontal scrollable tag pills on mobile, stacked header, touch-friendly targets
- **Agent authoring:** OpenClaw skill enables content creation via Telegram (voice or text input) — to be replaced by a self-contained agent with SQLite + vector memory (see issue #40)
- **AI tag suggestions:** After theme creation, `POST /api/themes/{id}/suggest-tags` returns 3–5 Claude Haiku-generated tags; two-phase create dialog pre-fills chip input with sparkle (✨) indicators per AI-suggested tag
- **Sidebar digest nav:** Monthly digest links in left sidebar smooth-scroll to digest position in feed (desktop only)
- **Theme permalinks:** Standalone `/themes/$themeId` pages for sharing individual themes, with hover-visible link icon in the feed
- **Image uploads:** Upload images/GIFs to Cloudflare R2 via `POST /api/uploads`, insert markdown image syntax into breadcrumbs

## Gotchas (Critical Agent Directives)

**SQLModel + SQLAlchemy 2.0 Compatibility:**
- Do NOT use `from __future__ import annotations` - causes relationship resolution errors
- Use explicit types: `List["Model"]` and `Optional[Type]` instead of `list["Model"]` and `Type | None`
- Add `# type: ignore` to relationship fields to suppress false type checker warnings
- SQLModel `Relationship()` doesn't accept SQLAlchemy parameters directly - use `sa_relationship_kwargs` dict:
  ```python
  # Wrong - TypeError
  Relationship(cascade="all, delete", passive_deletes=True)

  # Correct
  Relationship(sa_relationship_kwargs={"cascade": "all, delete", "passive_deletes": True})
  ```
- For cascade deletes: Use `ondelete="CASCADE"` in `Field()` for FK + `cascade` + `passive_deletes` in `Relationship()` (see `docs/solutions/cascade-patterns.md`)

**Pydantic Validators in SQLModel:**
- Field validators in base classes (table=False) don't apply to table models (table=True)
- Use `mode='before'` in `@field_validator` for pre-coercion validation
- Known limitation: Name normalization validators won't run on table models - needs custom save logic

**Module-level `os.getenv()` and `load_dotenv()` ordering:**
- `load_dotenv()` is called in `db.py`, but any module that reads env vars at import time (e.g. `auth.py`) may be imported *before* `db.py`
- If that happens, `os.getenv()` returns empty strings because `.env` hasn't been loaded yet
- Fix: any module that reads env vars at module level should call `load_dotenv()` itself before `os.getenv()`

**TanStack Router route tree must be committed:**
- `frontend/src/routeTree.gen.ts` is auto-generated during `vite dev` when route files change
- Docker builds run `tsc` before `vite build`, so the route tree must be pre-committed
- If you add a new route file, run `pnpm build` (or `mise run build`) locally and commit the updated `routeTree.gen.ts`

**Replicate theme image generation — two distinct 503 failure modes (`app/images/providers.py`):**
- Low account credit (<$5) triggers Replicate's own throttle; error text mentions the $5 threshold. Fix: top up billing at replicate.com, not a code change.
- Timeouts/network errors ("All N candidates failed: timed out...; Network error: The read operation timed out") are a *different* failure — check the Replicate dashboard balance first before assuming it's the credit issue.

**NEVER use `replicate.run()` here — it cannot be bounded from outside (`app/images/providers.py`):**
- `replicate.run()` defaults to `wait=True`, which sets the httpx read timeout to **60.5s** (`replicate/prediction.py::_create_prediction_timeout`). Any wall-clock timeout shorter than that always fires first, making retry logic unreachable dead code.
- Passing `wait=<int N>` does **not** fix it. When the long-poll expires with the prediction still `starting`, `run()` falls into `prediction.wait()`, a poll loop with **no timeout and no iteration cap**. That is exactly the accept-but-never-start pool failure we need to survive.
- So we drive `client.predictions.create(..., wait=False)` and poll on our own clock. That is the whole reason this class looks the way it does; do not "simplify" it back to `run()`.

**Replicate pools are a failover list, not a constant:**
- `DEFAULT_FLUX_MODELS` holds canonical `flux-schnell` and the `-lora` sibling. Both have wedged at different times (2026-05: canonical wedged, `-lora` healthy; 2026-07: exactly reversed, measured). A retry moves to the **next pool** — re-rolling the same wedged pool just buys another timeout.
- Diagnose with a 2-model probe before touching code: create one prediction per model, poll ~45s, see which ever leaves `starting`.

**Two different timeouts, because "queued forever" and "slow" are different failures:**
- `REPLICATE_STARTING_TIMEOUT_SECONDS` (15s): still in `starting` means never scheduled onto a GPU. Bail early and fail over.
- `REPLICATE_ATTEMPT_TIMEOUT_SECONDS` (40s): once `processing` it is genuinely rendering and deserves patience. A healthy cold start measured 25s, so a tighter bound would cancel work about to succeed *and still bill for it*.
- Abandoned predictions are **cancelled** (`prediction.cancel()`). A read timeout or wedge means the client gave up, not the prediction: it keeps running on GPU and billing until cancelled.
- The batch backstop is **derived**, never hand-set: `(max_attempts-1)*starting + attempt + max_attempts*http_read`. A backstop below the retry budget silently makes retries unreachable, which was the original bug.
- The backstop uses a **shared deadline** across candidates, not a fresh timeout per future. They run concurrently, so per-future timeouts let a wedged pool take `num_outputs * timeout` (4 x 60s = 4 min) to surface one error.

**Retry classification — `UNRECOVERABLE_STATUSES` is deliberate:**
- Retry: wedge, `ModelError`, `httpx.HTTPError`, 5xx, and **404**. 404 is not permanent here: Replicate returned "No adapter found for model" for a model that had succeeded minutes earlier, so it means "this pool is unreachable", which is precisely when to try the next one.
- Do NOT retry 400/401/402/403/422/429. These are identical on every model, so failover cannot help; it only doubles doomed calls. 402 is the out-of-credit signal that needs a top-up.

**Env knobs are validated, not raw `int()`:** `_env_number` falls back loudly on malformed or non-positive values. These are module-level constants, so a bare `int("25s")` would crash app startup, and `0` would disable the very bound it configures.

**Testing this file:** drive a scripted API through `httpx.MockTransport` (see `FakePool` in `tests/test_images.py`), never a fake that raises instantly. The original bug lived in the SDK's control flow and 49 green tests with instant-raising fakes coexisted with a fix that did nothing in production. Also keep test attempt timeouts short: `ThreadPoolExecutor` cannot cancel running threads and joins them at exit, so a long-running abandoned attempt adds invisible wall clock that pytest's own timings do not show.

## Deep-Dive References
- **Data model:** `docs/data-model.md`
- **Cascade delete patterns:** `docs/solutions/cascade-patterns.md`
- **Digests (weekly/monthly summaries):** `docs/digests.md`
- **Deployment gotchas:** `docs/solutions/deployment-gotchas.md`
