# Breadcrumbs Roadmap

## MVP (v0.1.0)

### Phase 1: Data Model
**Status:** Complete

SQLModel models (Theme, Breadcrumb, Tag, ThemeTag), cascade deletes,
PostgreSQL + Alembic migrations, 31 model tests.

### Phase 2: API Endpoints
**Status:** Complete

11 REST endpoints for themes, breadcrumbs, tags. Search, filtering,
pagination. 70 total tests.

### Phase 3: Frontend
**Status:** In progress

| Issue | Scope | Depends on |
|-------|-------|------------|
| [#9](https://github.com/meninoebom/breadcrumbs/issues/9) | Initialize frontend (Vite, TanStack, Tailwind, Shadcn) | -- |
| [#10](https://github.com/meninoebom/breadcrumbs/issues/10) | Reader stream view (themes + breadcrumbs) | #9 |
| [#11](https://github.com/meninoebom/breadcrumbs/issues/11) | Tag browsing, filtering, search | #10 |
| [#12](https://github.com/meninoebom/breadcrumbs/issues/12) | Writer dashboard + theme editor | #9 |

### Phase 4: Polish & Deploy
**Status:** Complete

- Global exception handlers ([#8](https://github.com/meninoebom/breadcrumbs/issues/8))
- CI/CD pipeline (GitHub Actions — backend + frontend in parallel)
- Railway deployment (single service, auto-deploy from main)
- Loading states, error handling, responsive design

## Post-MVP

### UI Polish
- Date nav sidebar — sticky left-column date navigator that highlights the current date section as the user scrolls, with forward/backward time navigation
- Tag search — search/filter within the tag sidebar as the list grows
- Markdown preview in editor
- Tag autocomplete
- Image upload

### Infrastructure
- Real authentication (OAuth/JWT)
- RSS feed
- Social sharing

### Input Surfaces
- Voice input — add breadcrumbs by talking to phone via Larry (agent-mediated voice capture)
- Project log funneling — post-PR learning journal entries auto-flow into breadcrumbs as new themes/crumbs

### Agent Integration
- Agent-native API — all content is markdown-backed, making the REST API naturally readable/writable by LLMs without serialization layers
- Chat bot on About page — trained on breadcrumbs, represents how I think; visitors can ask it questions about me, my work, or whether a role is a good fit
- Agent authoring — agents can create themes and breadcrumbs via the API (voice input, project log funneling, and chat bot all reduce to "agent POSTs markdown")
