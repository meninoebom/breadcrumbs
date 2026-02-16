# Breadcrumbs Roadmap

## Completed

- **Data model** — SQLModel models, cascade deletes, PostgreSQL + Alembic migrations
- **API** — 11 REST endpoints, search, filtering, pagination, 83 tests
- **Frontend** — Reader stream, writer dashboard, tag browsing, search
- **Deploy** — Railway, CI/CD, custom domain (crumb.blog)
- **Auth** — JWT auth protecting all mutating endpoints
- **Tag navigation** — Usage-based sorting, 5-tier opacity gradient, tag search
- **Tag authoring UX** — Chip input with typeahead suggestions, comma/Enter to commit
- **Agent authoring** — OpenClaw skill for creating content via Telegram (voice or text)
- **Mobile responsive** — Horizontal tag pill strip, stacked header, touch targets, responsive video embeds

## Up Next

### 1. Time-Based Navigation
Navigate the stream by time period — jump to a year, then drill into months. Low priority until the archive grows large enough to need it.

### 2. Always-On Agent
Run OpenClaw on a VPS or Mac Mini so the Telegram bot works when the laptop is closed. Currently agent only responds when the local machine is awake.

### 3. Tag Reordering
Drag-to-reorder tags in the sidebar and mobile pill strip. The horizontal pill layout is already compatible with dnd-kit sortable containers.
