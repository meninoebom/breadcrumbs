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
- **Theme Cover Images** — AI-generated cover images per theme via a Claude → Flux pipeline: Haiku 4.5 translates abstract theme text into a concrete scene, Flux Schnell renders it. Writer picks from a grid of 4, selected image is re-uploaded to R2 under an SSRF-guarded allowlist. Displayed as 56px thumbnails in the feed and 240px on permalink pages. DI-driven architecture (`app/images/` package) keeps providers swappable.

## Up Next

### Phase 4: AI Tag Suggestions

Auto-generate tags when a theme is written. After saving a theme, an AI call suggests 3–5 tags that auto-populate the tag input — writer removes unwanted ones before saving. Uses Claude API (Haiku model) with awareness of existing tags to prefer reuse.

- **4a.** Backend endpoint: `POST /api/themes/{id}/suggest-tags` (auth required)
- **4b.** Frontend: call suggest-tags after theme creation, pre-fill tag chip input with loading state

### Future

- **Digest regeneration** — Allow re-generating a draft digest to capture themes added after initial generation
- **Yearly summaries** — Progressive summarization from monthly summaries
- **Summary-to-theme linking** — Join table for traceability
- **Time-based navigation** — Navigate by year/month when the archive grows large

### Backlog

#### Always-On Agent
Run OpenClaw on a VPS or Mac Mini so the Telegram bot works when the laptop is closed. Currently agent only responds when the local machine is awake.

#### Tag Reordering
Drag-to-reorder tags in the sidebar and mobile pill strip. The horizontal pill layout is already compatible with dnd-kit sortable containers.
