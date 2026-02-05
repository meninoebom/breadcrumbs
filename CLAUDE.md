# Claude Development Guide

## Project Overview
**Name:** Breadcrumbs
**Description:** A blog of collected breadcrumbs organized into themes. Based on a public Google doc maintained by a Google PM, this app makes it easy to create themes, add small thought atoms (breadcrumbs) to them, tag themes, and read through published content in a continuous stream format.
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
- **Theme-based organization:** Breadcrumbs grouped by theme, themes are tagged and searchable
- **Chronological display:** Themes and their breadcrumbs presented as continuous stream with clear theme boundaries
- **Markdown support:** All content rendered as markdown
- **Draft/publish workflow:** Themes can be drafted and published; readers only see published themes

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
- **Theme creation:** Writers create themes as containers for related breadcrumbs
- **Breadcrumb authoring:** Add small individual thought atoms (breadcrumbs) to themes
- **Tag-based organization:** Tags applied at theme level for filtering and discovery
- **Draft/publish workflow:** Writers can draft themes before publishing to readers
- **Authenticated editing:** Writers login to see unpublished themes and edit existing ones
- **Easy to read:** Continuous stream presentation with clear theme boundaries (not traditional blog articles)
- **Tag browsing:** Readers browse tags alphabetically and filter themes by tag
- **Search:** Full-text search across theme titles, breadcrumb content, and tags
- **Timestamps:** Every breadcrumb has a timestamp
- **Markdown rendering:** Full markdown support for formatting

### Key Design Decisions
- **Visual style:** Reads like one long rant/stream-of-consciousness rather than discrete articles
- **Inspired by Google Docs approach:** Based on a public PM's running document
- **PostgreSQL for search:** Leverage full-text search capabilities
- **SQLModel ORM:** Type-safe database operations with Pydantic integration
- **TanStack ecosystem:** Modern React state and routing without heavy framework
- **Shadcn UI:** Copy-paste components for customization instead of npm dependency

### Data Model
**Theme:**
- `id` - Primary key
- `title` - Required display name for the theme (e.g., "React Hooks Deep Dive", "Morning Thoughts on Architecture")
- `description_md` - Optional markdown intro/context for the theme
- `visibility` - Enum: draft or published (controls reader visibility)
- `created_at` - When theme was created
- `updated_at` - Last modified datetime
- `breadcrumbs` - Relationship to breadcrumbs (one-to-many)
- `tags` - Relationship to tags (many-to-many via ThemeTag)
- **Purpose:** Topical container for related breadcrumbs. Themes are the primary organizational unit, providing clear boundaries in the continuous stream. Tags and visibility are managed at theme level.

**Breadcrumb:**
- `id` - Primary key
- `body_md` - Markdown text (the actual thought/content atom)
- `created_at` - Created datetime
- `updated_at` - Last modified datetime
- `theme_id` - Foreign key to Theme (required, one-to-many)
- **Purpose:** Small individual thought atoms that belong to a theme. Visibility is inherited from parent theme.

**Tag:**
- `id` - Primary key
- `name` - Tag name (normalized: lowercase, dashes, unique)
- `themes` - Relationship to themes (many-to-many via ThemeTag)

**ThemeTag (join table):**
- `theme_id` - Foreign key to Theme
- `tag_id` - Foreign key to Tag

**Relationship Design:**
- **Themes = Topical grouping**: Container for related breadcrumbs with title, tags, and visibility
- **Breadcrumbs = Content atoms**: Individual thoughts that belong to exactly one theme
- **Tags = Discovery mechanism**: Applied to themes for filtering and browsing
- Themes must have a title and can have 0+ tags
- Breadcrumbs must belong to exactly one theme
- Only published themes (and their breadcrumbs) are visible to readers
- Writers see both draft and published themes when authenticated

### Common Patterns

**Cascade Delete (Hybrid Approach):**
Use three together for proper cascade delete behavior:
1. **Database level:** `ondelete="CASCADE"` in `Field()` - enforces at SQL level
2. **ORM awareness:** `cascade="all, delete[-orphan]"` in relationship - tells SQLAlchemy what's happening
3. **Efficiency:** `passive_deletes=True` - uses DB cascade for unloaded collections

**When to use `delete-orphan`:**
- Existential dependency (child can't exist without parent)
- Example: Breadcrumb → Theme (breadcrumb without theme is invalid)
- Deletes children when removed from collection OR parent deleted

**When to use `delete` only:**
- Independent entities with associations
- Example: Theme ↔ Tag (both exist independently)
- Deletes association only, not the entities themselves

**Example:**
```python
# One-to-many with orphan deletion (Theme → Breadcrumbs)
breadcrumbs: List["Breadcrumb"] = Relationship(
    back_populates="theme",
    sa_relationship_kwargs={
        "cascade": "all, delete-orphan",
        "passive_deletes": True,
    }
)

# Many-to-many without orphan deletion (Theme ↔ Tags)
tags: List["Tag"] = Relationship(
    back_populates="themes",
    link_model=ThemeTag,
    sa_relationship_kwargs={
        "cascade": "all, delete",
        "passive_deletes": True,
    }
)
```

**PostgreSQL Table Naming:**
- Explicitly set `__tablename__` for join tables to follow snake_case convention
- Example: `__tablename__ = "theme_tag"` (not auto-generated "themetag")
- Improves readability in psql and aligns with PostgreSQL conventions

### Gotchas & Known Issues

**SQLModel + SQLAlchemy 2.0 Compatibility:**
- Do NOT use `from __future__ import annotations` - causes relationship resolution errors
- Use explicit types: `List["Model"]` and `Optional[Type]` instead of `list["Model"]` and `Type | None`
- Add `# type: ignore` to relationship fields to suppress false type checker warnings
- SQLModel `Relationship()` doesn't accept SQLAlchemy parameters directly - use `sa_relationship_kwargs` dict:
  ```python
  # ❌ Wrong - TypeError
  Relationship(cascade="all, delete", passive_deletes=True)

  # ✅ Correct
  Relationship(
      sa_relationship_kwargs={
          "cascade": "all, delete",
          "passive_deletes": True,
      }
  )
  ```
- For cascade deletes: Use `ondelete="CASCADE"` in `Field()` for FK + `cascade` + `passive_deletes` in `Relationship()` (see Common Patterns)

**Pydantic Validators in SQLModel:**
- Field validators in base classes (table=False) don't apply to table models (table=True)
- Use `mode='before'` in `@field_validator` for pre-coercion validation
- Known limitation: Name normalization validators won't run on table models - needs custom save logic

**Testing with SQLite:**
- SQLite doesn't preserve timezone info on datetime fields
- Use in-memory database (`:memory:`) for fast, isolated tests
- StaticPool required for in-memory SQLite with SQLModel
