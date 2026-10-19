# Spec: Authoring Connector (phone authoring over MCP)

Purpose: Let Brandon author and manage crumb.blog content from his phone by
talking to an agent (Claude app custom connector). A small MCP server is mounted
on the existing FastAPI app and exposes a focused set of authoring tools,
reusing the existing API-key admin auth. This covers the text operations;
cover images are specified separately.

Out of scope:
- A new mobile review UI (the existing writer dashboard is mobile-responsive; drafts are reviewed there).
- Delete operations (no destructive tools in v1).
- OAuth / dynamic client registration (a static connector token is sufficient for a single user).
- Tag drag-to-reorder, digests, subscribers.
- The dormant Telegram authoring agent (superseded by this, not touched here).

| ID | Criterion |
|----|-----------|
| CONN-1 | WHEN a client connects to the MCP endpoint without a valid connector token THEN the request is rejected and no tools are exposed |
| CONN-2 | WHEN a client connects with the valid connector token THEN the server lists the authoring tools over Streamable HTTP |
| CONN-3 | WHEN any authoring tool performs a write THEN it authenticates to the Breadcrumbs API as an admin machine client (X-API-Key), so an unauthenticated path cannot write |
| CAP-1 | WHEN `add_breadcrumb` is called with a valid theme id and content THEN a breadcrumb is created on that theme and its id and timestamp are returned |
| CAP-2 | WHEN `add_breadcrumb` references a non-existent theme id THEN the tool returns a clear not-found error, not a 500 |
| CAP-3 | WHEN `create_theme` is called with a title and no publish flag THEN the theme is created as a draft (published=false) |
| CAP-4 | WHEN `create_theme` is called with publish=true THEN the theme is created published and visible to readers |
| CAP-5 | WHEN `suggest_tags` is called for a theme THEN AI-suggested tags are returned for confirmation before any are applied |
| FIND-1 | WHEN `list_recent_themes` is called THEN it returns recent themes with id, title, published state, and tags, most recent first |
| FIND-2 | WHEN `search_themes` is called with a query THEN it returns themes matching across theme body, breadcrumb content, and tags |
| EDIT-1 | WHEN `update_breadcrumb` is called with a valid id and new content THEN the breadcrumb content is replaced and the updated record is returned |
| EDIT-2 | WHEN `update_theme` is called with a valid id and fields THEN only the provided fields change |
| PUB-1 | WHEN `publish_theme` is called on a draft THEN published becomes true and the theme is reader-visible |
| PUB-2 | WHEN `unpublish_theme` is called on a published theme THEN published becomes false and it leaves the reader feed |

Needs human judgment (no contract ID, route to `needs-eyes`):
- Tool descriptions and the server-provided authoring prompt carry Brandon's voice and the reuse-existing-tags rule, so phone content matches the blog.
- `publish_theme`, `unpublish_theme`, and the edit tools confirm the target before acting, because voice capture is lossy.
