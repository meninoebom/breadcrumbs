# Breadcrumbs

> Traveler, there is no path. The path is made by walking.

**Live:** [crumb.blog](https://crumb.blog)

## What is this?

Breadcrumbs is a stream-of-consciousness blog where thoughts are organized into themes, and themes contain small thought atoms called breadcrumbs. Unlike traditional blogs with discrete articles, it reads as one continuous flow.

Inspired by [a public Google Doc](https://docs.google.com/document/d/1GrEFrdF_IzRVXbGH1lG0aQMlvsB71XihPPqQN-ONTuo/edit?tab=t.0) maintained by a Google PM.

## Tech Stack

- **Backend:** Python 3.13, FastAPI, PostgreSQL, SQLModel (managed with `uv`)
- **Frontend:** React 19, TanStack Router/Query, Tailwind CSS, Shadcn UI, Vite (on `pnpm`)
- **Deployment:** Railway, built from the committed `Dockerfile`, deployed by GitHub Actions on push to `main`
- **Domain:** [crumb.blog](https://crumb.blog) via CNAME to Railway

## Development

Toolchain versions are pinned in `mise.toml`, so [mise](https://mise.jdx.dev) sets up
both halves and runs them together:

```bash
mise install    # node 22, pnpm 10.33.0, python 3.13, uv
mise run dev    # frontend + backend
mise run check  # lint, types, and tests — the gate before committing
```

Running them separately:

```bash
# Backend (from project root)
uv sync
uv run dev  # http://localhost:8100

# Frontend — pnpm, not npm (the version is pinned via packageManager)
cd frontend
pnpm install
pnpm dev  # http://localhost:5173
```

See `CLAUDE.md` for conventions and `docs/roadmap.md` for what's next.
