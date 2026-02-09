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
**Status:** Not started

- Global exception handlers ([#8](https://github.com/meninoebom/breadcrumbs/issues/8))
- CI/CD pipeline
- Docker setup
- Loading states, error handling, responsive design

## Post-MVP

- Real authentication (OAuth/JWT)
- Markdown preview in editor
- Tag autocomplete
- Image upload
- RSS feed
- Social sharing
