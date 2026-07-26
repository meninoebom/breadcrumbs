# Deployment gotchas

## Production is built from a committed Dockerfile (2026-07)

Production deploys on Railway build from the repo's multi-stage `Dockerfile`. Every
tool version is pinned in-repo: Node 22, pnpm 10.33.0, Python 3.13, uv 0.8.12.
`railway.toml` sets `builder = "dockerfile"`. Runtime config (`PORT`, `ENVIRONMENT`,
`DATABASE_URL`, secrets) is injected by Railway; nothing sensitive is in the image.

To validate a build change before pushing:

```bash
docker build -t bc-test .
# migrations are Postgres-only, so test against Postgres, not SQLite:
docker network create bc-net
docker run -d --name bc-pg --network bc-net \
  -e POSTGRES_PASSWORD=pw -e POSTGRES_USER=bc -e POSTGRES_DB=breadcrumbs postgres:16-alpine
docker run --rm --network bc-net -p 8199:8199 \
  -e ENVIRONMENT=production -e PORT=8199 \
  -e DATABASE_URL="postgresql://bc:pw@bc-pg:5432/breadcrumbs" \
  -e JWT_SECRET=x -e ADMIN_PASSWORD=x bc-test
# then: curl localhost:8199/ (SPA), curl localhost:8199/api/themes (JSON)
```

## Why we do NOT use Nixpacks or corepack (postmortem, 2026-07)

The build used to be Nixpacks with `corepack enable && pnpm install`. It silently
broke every deploy for ~2 months after the pnpm migration. Two independent causes:

1. **Nixpacks defaulted to Node 18.** Vite 7 needs >= 20.19. Nothing in the repo
   pinned the Node version (Nixpacks does not read `mise.toml`), so the wrong version
   was chosen invisibly.
2. **`corepack enable` failed with "Cannot find matching keyid".** corepack pins npm
   registry signing keys, npm rotated them, and the bundled corepack (through Node
   22.11) rejected the pnpm download. The only Nixpacks workaround was
   `COREPACK_INTEGRITY_KEYS=0`, i.e. disabling signature verification: a band-aid on
   a security control.

Both are gone with the Dockerfile: Node is pinned to 22, and pnpm is installed
directly (`npm i -g pnpm@10.33.0`), which never invokes corepack's signing check.

**Rule:** do not reintroduce Nixpacks, corepack, or `COREPACK_INTEGRITY_KEYS` here.
If pnpm needs bumping, change the pinned version in both `Dockerfile` and
`frontend/package.json`'s `packageManager` field.

## The build broke silently because deploy failures were invisible

The 2-month gap was not just a broken build; nobody noticed because a failed Railway
build leaves the previous deployment serving, with no signal in GitHub. Two defenses:

- After merging anything that touches the build, confirm a new deployment actually
  went live (check the Railway dashboard, or `railway deployment list`).
- **Fixed 2026-07-25:** deploys now run from `.github/workflows/deploy.yml` on push to
  `main`, so a failed deploy is a red X on the commit instead of silence. Railway's
  native git trigger stays disconnected on purpose; re-enabling it would both restore
  the silent-failure mode and cause double deploys. See the deploy section of
  `CLAUDE.md` for the token setup and rotation steps.

## `railway up` from an unlinked directory creates a new project

Running `railway up` in a directory with no linked project does not error. It
silently **creates a new Railway project named after the current folder** and deploys
there. Always `railway link -p <project> -e <env> -s <service>` first, and confirm the
build-log URL's project id before trusting a CLI deploy.

### Why this keeps happening: links are keyed by absolute path, globally

The link is not stored in the repo. There is no `.railway/` directory here and nothing
in git marks this checkout as linked. Railway records links in a single global file,
`~/.railway/config.json`, keyed by **absolute directory path**:

```json
"/Users/brandon/dev/breadcrumbs": { "name": "Breadcrumbs", "project": "0afd3e64-...", ... }
```

Three consequences, all of which have bitten this project:

1. **Every git worktree is a separate, unlinked directory.** A worktree of this repo
   shares the git history but has a different absolute path, so it starts with no
   Railway link. This is how the stray `cottontail-butte` project was created: a
   `railway up` from a fresh warp worktree of that name.
2. **Agent scratchpad directories are also unlinked paths**, and they get linked by
   accident. The config currently contains an entry for a
   `/private/tmp/claude-501/.../scratchpad/rw` path pointing at Breadcrumbs.
3. **Entries survive directory deletion.** Most paths in the file no longer exist, so
   the config accumulates stale links and gives a misleading picture of what is wired
   to what.

The dangerous case is `/private/tmp` being linked to an unrelated project
(`Bad Landlord Report` at time of writing). A `railway up` run from a scratchpad root
would not create a new project and would not prompt. It would deploy this repo's code
into that unrelated project.

**Rule: run `railway` commands only from `/Users/brandon/dev/breadcrumbs`.** Not from a
worktree, not from a scratchpad. Before any CLI deploy, confirm the target:

```bash
railway status          # must print Project: Breadcrumbs, Environment: production
```

To audit which paths are linked and which are stale:

```bash
python3 -c "
import json,os
d=json.load(open(os.path.expanduser('~/.railway/config.json')))
for p,v in d.get('projects',{}).items():
    print(('EXISTS ' if os.path.isdir(p) else 'GONE   ')+p+'  -> '+v.get('name','?'))
"
```

## Migrations are Postgres-only

At least one Alembic migration uses Postgres-specific SQL
(`2026_02_10...merge_theme_title_and_description`). It fails on SQLite with a syntax
error. Local smoke tests of the full startup path must run against Postgres.
