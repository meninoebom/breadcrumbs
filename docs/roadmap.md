# Breadcrumbs Roadmap

## Completed

- **Data model** — SQLModel models, cascade deletes, PostgreSQL + Alembic migrations
- **API** — 11 REST endpoints, search, filtering, pagination, 83 tests
- **Frontend** — Reader stream, writer dashboard, tag browsing, search
- **Deploy** — Railway, CI/CD, custom domain (crumb.blog)
- **Auth** — JWT auth protecting all mutating endpoints

## Up Next

### 1. Agent Authoring — OpenClaw Integration
Connect the OpenClaw agent so it can create themes and breadcrumbs via the API. The REST API is already agent-friendly (markdown in, markdown out) — this is about wiring up the agent to POST content autonomously.

### 2. Tag Navigation Improvements
Upgrade the tag sidebar for discovery and scale:
- **Sort by usage** — most-used tags first instead of alphabetical
- **Visual indicator** — small bar, count badge, or similar treatment beside each tag showing relative usage
- **Tag search** — filter/typeahead field above the tag list so readers can find tags quickly as the list grows

The `/api/tags` endpoint already returns `theme_count` per tag, so sorting and indicators are purely frontend. Tag search may also be frontend-only (client-side filter) unless the list gets very large.

### 3. Tag Authoring UX
Improve the tag input experience in the writer:
- **Typeahead** — suggest existing tags as the writer types
- **Chip behavior** — after typing a comma (or selecting a suggestion), the tag solidifies into a visual chip so the writer can see at a glance whether it matched an existing tag or will create a new one
- **Goal:** Reduce accidental tag duplication from typos

### 4. Time-Based Navigation
Navigate the stream by time period — jump to a year, then drill into months. Low priority until the archive grows large enough to need it.
