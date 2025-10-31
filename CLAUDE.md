# Claude Development Guide

## Project Overview
**Name:** Breadcrumbs
**Description:** A blog of collected crumbs that reads like one long rant. Based on a public Google doc maintained by a Google PM, this app makes it easy to timestamp, tag, search, and read through stream-of-consciousness thoughts in markdown format.
**Inspiration:** https://docs.google.com/document/d/1GrEFrdF_IzRVXbGH1lG0aQMlvsB71XihPPqQN-ONTuo/edit?tab=t.0

**Tech Stack:**
- **Backend:** Python, FastAPI, PostgreSQL, SQLModel
- **Frontend:** TanStack Router, TanStack Query, Tailwind CSS, Shadcn UI

## Development Workflow

This project uses AI-assisted development with the following structure:
- `CLAUDE.md` (this file) - Project conventions and patterns
- `llms.txt` - Public documentation for LLM discovery
- `.llm/` - Private workspace for active development state (gitignored)
  - `active-plan.md` - Current work, TODOs, blockers
  - `codebase-overview.md` - Living architectural analysis

## Code Conventions

### Python Backend (FastAPI)
- Use `snake_case` for variables, functions, and file names
- Use `PascalCase` for classes and SQLModel models
- Type hints required for all function signatures
- Format with `black` and `ruff`
- Follow FastAPI best practices for dependency injection
- SQLModel for ORM (combines SQLAlchemy + Pydantic)

**File Structure:**
```
/backend
  /app
    /api       - API routes
    /models    - SQLModel database models
    /schemas   - Pydantic schemas for validation
    /core      - Config, database, deps
    /services  - Business logic
```

### TypeScript Frontend (React)
- Use `PascalCase` for components
- Use `camelCase` for variables and functions
- Prefer function components with hooks
- TanStack Router for file-based routing
- TanStack Query for server state management
- Tailwind CSS for styling
- Shadcn UI for component primitives

**File Structure:**
```
/frontend
  /src
    /routes       - TanStack Router file-based routes
    /components   - Reusable React components
    /lib          - Utilities and helpers
    /hooks        - Custom React hooks
```

### Architecture Patterns
- **Full-stack separation:** Backend and frontend in separate directories
- **API-first design:** Backend exposes RESTful JSON API
- **Tag-based organization:** Crumbs are tagged and searchable
- **Chronological display:** Crumbs presented as continuous stream with timestamps
- **Markdown support:** All content rendered as markdown

### Testing Strategy
- **Backend:** pytest for unit and integration tests
- **Frontend:** Vitest + React Testing Library
- **Coverage target:** 70%+ for critical paths
- **E2E:** Playwright for key user flows

### Git Workflow
- Branch naming: `feature/description` or `fix/description`
- Commit format: `type: description` (feat, fix, docs, refactor, test)
- PR requirements: [Define review process as team grows]

## Key Commands

Useful slash commands for this project:
- `/create-active-plan` - Update work plan with codebase research
- `/generate-codebase-overview` - Regenerate architectural overview
- `/work-gh-issue [number]` - Implement GitHub issue on feature branch
- `/dev-experiment [goal]` - Experiment-driven development with feedback loop
- `/create-gh-issue-from-active-plan` - Create GitHub issues from active plan

## Project-Specific Notes

### Core Features
- **Tag-based search:** Filter crumbs by tags
- **Easy to add:** Quick input for new crumbs with markdown support
- **Easy to read:** Continuous stream presentation (not traditional blog articles)
- **Timestamps:** Every crumb has a timestamp
- **Markdown rendering:** Full markdown support for formatting
- **Unit-based organization:** Crumbs broken up by unit and date while maintaining flow

### Key Design Decisions
- **Visual style:** Reads like one long rant/stream-of-consciousness rather than discrete articles
- **Inspired by Google Docs approach:** Based on a public PM's running document
- **PostgreSQL for search:** Leverage full-text search capabilities
- **SQLModel ORM:** Type-safe database operations with Pydantic integration
- **TanStack ecosystem:** Modern React state and routing without heavy framework
- **Shadcn UI:** Copy-paste components for customization instead of npm dependency

### Data Model
**Crumb:**
- `id` - Primary key
- `body_md` - Markdown text
- `created_at` - Created datetime
- `updated_at` - Last modified datetime
- `visibility` - Enum: draft or published
- `unit_id` - Foreign key to Unit (optional, one-to-many)
- `tags` - Relation to tags (many-to-many via CrumbTag)

**Unit:**
- `id` - Primary key
- `name` - Display name for the writing session (e.g., "react-hooks", "morning-thoughts")
- `created_at` - When this session was started
- `crumbs` - Relationship to crumbs (one-to-many)
- **Purpose:** Groups related crumbs from a single writing session. Same display name can be reused across different sessions (different created_at timestamps create distinct units). This provides visual grouping in the chronological stream while maintaining continuous flow.

**Tag:**
- `id` - Primary key
- `name` - Tag name (normalized: lowercase, dashes, unique)
- Relationship to crumbs (many-to-many via CrumbTag)

**CrumbTag (join table):**
- `crumb_id` - Foreign key to Crumb
- `tag_id` - Foreign key to Tag

**Relationship Design:**
- **Units = Temporal grouping** (when): Writing sessions, visually separated in stream
- **Tags = Topical grouping** (what): Topic relationships across all sessions
- Crumbs can have zero or one Unit (optional session grouping)
- Crumbs can have multiple Tags (flexible categorization)

### Common Patterns
[To be documented as patterns emerge during development]

### Gotchas & Known Issues
[Document any quirks, workarounds, or things to watch out for]
