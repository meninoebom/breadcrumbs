# Data Model

## Theme
- `id` - Primary key
- `body_md` - Required markdown content (the thought itself, e.g., "The past and future are ghosts...")
- `visibility` - Enum: draft or published (controls reader visibility)
- `created_at` - When theme was created
- `updated_at` - Last modified datetime
- `breadcrumbs` - Relationship to breadcrumbs (one-to-many)
- `tags` - Relationship to tags (many-to-many via ThemeTag)
- **Purpose:** A thought that can have sub-thoughts (breadcrumbs). Themes are the primary organizational unit. Tags and visibility are managed at theme level.

## Breadcrumb
- `id` - Primary key
- `body_md` - Markdown text (the actual thought/content atom)
- `created_at` - Created datetime
- `updated_at` - Last modified datetime
- `theme_id` - Foreign key to Theme (required, one-to-many)
- `parent_id` - Optional FK to another Breadcrumb (self-referential, adjacency list pattern)
- **Purpose:** Small individual thought atoms that belong to a theme. Breadcrumbs can nest: a breadcrumb with `parent_id` is a reply/elaboration on another breadcrumb. `parent_id` is immutable after creation. Visibility is inherited from parent theme.

## Tag
- `id` - Primary key
- `name` - Tag name (normalized: lowercase, dashes, unique)
- `position` - Optional int for writer-defined custom ordering (nullable; set via `PATCH /api/tags/reorder`)
- `themes` - Relationship to themes (many-to-many via ThemeTag)

## ThemeTag (join table)
- `theme_id` - Foreign key to Theme
- `tag_id` - Foreign key to Tag

## Relationship Design
- **Themes = Thoughts**: Primary content units with body, tags, and visibility
- **Breadcrumbs = Sub-thoughts**: Individual thought atoms that belong to exactly one theme
- **Breadcrumb nesting**: Breadcrumbs can have parent-child relationships (adjacency list). Parent must be in the same theme. Cascade delete: deleting a parent deletes all children. Depth soft-limited to 10 at the API level.
- **Tags = Discovery mechanism**: Applied to themes for filtering and browsing
- Themes must have body_md and can have 0+ tags
- Breadcrumbs must belong to exactly one theme
- Only published themes (and their breadcrumbs) are visible to readers
- Writers see both draft and published themes when authenticated
