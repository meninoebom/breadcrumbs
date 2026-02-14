# Breadcrumbs

> A blog of collected crumbs that reads like one long rant

**Live:** [crumb.blog](https://crumb.blog)

## What is this?

Breadcrumbs is a stream-of-consciousness blog where thoughts are organized into themes, and themes contain small thought atoms called breadcrumbs. Unlike traditional blogs with discrete articles, it reads as one continuous flow.

Inspired by [a public Google Doc](https://docs.google.com/document/d/1GrEFrdF_IzRVXbGH1lG0aQMlvsB71XihPPqQN-ONTuo/edit?tab=t.0) maintained by a Google PM.

## Tech Stack

- **Backend:** Python, FastAPI, PostgreSQL, SQLModel
- **Frontend:** React, TanStack Router/Query, Tailwind CSS, Shadcn UI
- **Deployment:** Railway (single service, auto-deploy from main)
- **Domain:** [crumb.blog](https://crumb.blog) via CNAME to Railway

## Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload  # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev  # http://localhost:5173
```

See `CLAUDE.md` for conventions and `docs/roadmap.md` for what's next.
