# Claude Development Guide

## Project Overview
**Name:** Breadcrumbs
**Description:** A blog of collected breadcrumbs organized into themes. Based on a public Google doc maintained by a Google PM, this app makes it easy to create themes, add small thought atoms (breadcrumbs) to them, tag themes, and read through published content in a continuous stream format.
**Inspiration:** https://docs.google.com/document/d/1GrEFrdF_IzRVXbGH1lG0aQMlvsB71XihPPqQN-ONTuo/edit?tab=t.0

**Tech Stack:**
- **Backend:** Python, FastAPI, PostgreSQL, SQLModel
- **Frontend:** TanStack Router, TanStack Query, Tailwind CSS, Shadcn UI

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
- If you add a new route file, run `npm run build` locally and commit the updated `routeTree.gen.ts`

## Deep-Dive References
- **Data model:** `docs/data-model.md`
- **Cascade delete patterns:** `docs/solutions/cascade-patterns.md`
- **Digests (weekly/monthly summaries):** `docs/digests.md`
- **Deployment gotchas:** `docs/solutions/deployment-gotchas.md`
