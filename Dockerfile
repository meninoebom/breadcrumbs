# syntax=docker/dockerfile:1
#
# Reproducible production image for the breadcrumbs polyglot app (FastAPI backend +
# Vite/React frontend). Every tool version is pinned here in-repo so the build can
# never silently drift the way the previous Nixpacks setup did (it defaulted to
# Node 18 and stayed broken for two months). No corepack: pnpm is installed
# directly at its pinned version, which sidesteps corepack's signing-key
# verification entirely rather than disabling it.

# ---------- Stage 1: build the frontend ----------
FROM node:22-slim AS frontend

WORKDIR /build

# pnpm pinned to the exact version in frontend/package.json's packageManager field.
RUN npm install --global pnpm@10.33.0

# Install dependencies first, on just the manifest + lockfile, so this layer is
# cached until the dependency set actually changes.
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Build the SPA. `pnpm build` runs `tsc -b && vite build`, emitting to /build/dist.
COPY frontend/ ./
RUN pnpm build

# ---------- Stage 2: python runtime ----------
FROM python:3.13-slim AS runtime

# uv pinned to match the version the project builds with; copied from the official
# uv image so we never fetch-and-hope at build time.
COPY --from=ghcr.io/astral-sh/uv:0.8.12 /uv /uvx /bin/

WORKDIR /app

# Compile bytecode for faster cold starts; copy (not hardlink) since the build
# context and venv live on different layers.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Resolve dependencies from the lockfile before copying the app source, so a code
# change doesn't invalidate the (slow) dependency layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Backend source + migration assets. STATIC_DIR in app/api.py resolves to
# <app parent>/frontend/dist, i.e. /app/frontend/dist, so the built SPA lands there.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini main.py ./
COPY --from=frontend /build/dist ./frontend/dist

# Install the project itself now that its package source is present.
RUN uv sync --frozen --no-dev

# Railway injects PORT and every secret/config var (ENVIRONMENT, DATABASE_URL, R2_*,
# ANTHROPIC_API_KEY, REPLICATE_API_TOKEN, ...) at runtime, so none are baked in here.
# Migrations run on start; then the app boots. main.py reads PORT and binds 0.0.0.0.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python main.py"]
