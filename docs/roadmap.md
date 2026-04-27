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
- **Weekly Digests** — AI-generated weekly summaries interleaved in reader feed, admin digest management in writer dashboard, APScheduler for automated generation (Sunday) and send (Tuesday), email subscriptions with double opt-in, detail drill-down page
- **Monthly Digests** — Progressive summarization (monthly summaries generated from weekly summaries), DigestType enum (weekly/monthly), scheduler job on 1st of month, AI-generated indicator (sparkles icon) on all summary cards
- **Navigation & Permalinks** — Sidebar digest nav (monthly digest links with smooth-scroll), theme permalink pages (`/themes/$themeId`), hover-visible permalink icons on themes, DOM anchor IDs on all feed items
- **Image Uploads** — Upload images/GIFs to Cloudflare R2 via writer dashboard, markdown image syntax inserted into breadcrumbs
- **AI Tag Suggestions** — After theme creation, Claude Haiku suggests 3–5 reuse-aware tags; two-phase create dialog pre-fills the chip input with sparkle indicators; writer can edit before saving

## Up Next

### Phase 5: Tag Reordering

Drag-to-reorder tags in both the sidebar and mobile pill strip. Order stored server-side so readers see the same ordering across all devices.

- New `position` column on the Tag model with migration
- `PATCH /api/tags/reorder` endpoint (auth required)
- dnd-kit sortable containers in sidebar and tag bar
- Feed and tag list respect server-side sort order

### Future

- **Digest regeneration** — Allow re-generating a draft digest to capture themes added after initial generation
- **Yearly summaries** — Progressive summarization from monthly summaries
- **Summary-to-theme linking** — Join table for traceability
- **Time-based navigation** — Navigate by year/month when the archive grows large

### Backlog

#### Always-On Blog Authoring Agent
A self-contained Telegram bot (not OpenClaw) with persistent memory via SQLite + vector embeddings. Responds 24/7 from a VPS or Mac Mini. Tools: create theme, add breadcrumb, list recent themes, semantic search over content. Hosting TBD.

#### Tag Reordering
Drag-to-reorder tags in the sidebar and mobile pill strip. The horizontal pill layout is already compatible with dnd-kit sortable containers.
