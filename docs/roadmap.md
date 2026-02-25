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

### Phase 4: AI Tag Suggestions

Auto-generate tags when a theme is written. After saving a theme, an AI call suggests 3–5 tags that auto-populate the tag input — writer removes unwanted ones before saving. Uses Claude API (Haiku model) with awareness of existing tags to prefer reuse.

- **4a.** Backend endpoint: `POST /api/themes/{id}/suggest-tags` (auth required)
- **4b.** Frontend: call suggest-tags after theme creation, pre-fill tag chip input with loading state

### Phase 5: Weekly Summaries

A new content type — AI-generated weekly summaries — that appears inline in the reader stream alongside themes. Designed agent-native so an external agent can create summaries via the API.

- **5a.** `WeeklySummary` model + Alembic migration (title, body_md, week_start, week_end, visibility)
- **5b.** CRUD endpoints (`/api/summaries`) + context endpoint (`/api/summaries/context`) for agent to gather that week's themes/breadcrumbs
- **5c.** Frontend: interleave summaries in the reader stream with distinct visual treatment, plus detail route

### Phase 6: Weekly Summary Agent Script

Standalone script that authenticates, fetches the week's context, calls Claude to generate a summary, and creates it as a draft. Run manually at first, wire to Railway cron later.

### Future

- **Email subscriptions** — subscriber model, email collection UI, unsubscribe
- **Email delivery** — Resend/Postmark integration, send summary on publish
- **Cron automation** — Railway cron to trigger weekly summary generation
- **Summary-to-theme linking** — join table for traceability

---

### Backlog

#### Time-Based Navigation
Navigate the stream by time period — jump to a year, then drill into months. Low priority until the archive grows large enough to need it.

#### Always-On Agent
Run OpenClaw on a VPS or Mac Mini so the Telegram bot works when the laptop is closed. Currently agent only responds when the local machine is awake.

#### Tag Reordering
Drag-to-reorder tags in the sidebar and mobile pill strip. The horizontal pill layout is already compatible with dnd-kit sortable containers.
