# Phone authoring via MCP connector

An MCP server mounted at `/mcp` lets an agent (the Claude app as a custom
connector) author crumb.blog content from a phone. Spec:
`docs/specs/authoring-connector.md`. Server: `app/mcp_server.py`.

## Security model

One auth gate. Every request to `/mcp` must carry a bearer token matching
`MCP_CONNECTOR_TOKEN`, verified at the transport by `StaticTokenVerifier`. Past
that gate the tools run in-process as the trusted admin principal, writing
through the same handlers the REST API uses. There is no second credential.

Fail-safe: when `MCP_CONNECTOR_TOKEN` is unset, the server is not built and
`/mcp` is never mounted. The app still boots and behaves exactly as before. So
the feature deploys dark and stays inert until the token is set.

## The connector token

The token is a shared secret you mint. It is not issued by Anthropic, Railway,
or Doppler. The same random string lives in two places:

1. Server side (`MCP_CONNECTOR_TOKEN` in Doppler + Railway): the server accepts
   only this string.
2. Client side (the custom connector config in your Claude account): the Claude
   app sends this string as its bearer token on every request.

### Provisioning (one time)

Generate it, write it to Doppler (system of record), then set it as a Railway
runtime var (the app reads env from Railway, not Doppler). Setting the Railway
var triggers a redeploy and `/mcp` goes live.

```bash
TOKEN=$(openssl rand -hex 32)
printf '%s' "$TOKEN" | doppler secrets set MCP_CONNECTOR_TOKEN -p breadcrumbs -c prd --silent
RAILWAY_TOKEN=$(doppler secrets get RAILWAY_TOKEN -p breadcrumbs -c prd --plain) \
  railway variables --set "MCP_CONNECTOR_TOKEN=$TOKEN" --service "Breadcrumbs Web App Server"
unset TOKEN
```

Retrieve the value when you need to paste it into the connector:

```bash
doppler secrets get MCP_CONNECTOR_TOKEN -p breadcrumbs -c prd --plain
```

Rotating is the same as any secret: generate a new token, overwrite both
places, then update the bearer token in the Claude connector config.

## Adding the connector in Claude

Custom connectors are added on claude.ai web or desktop first; once added they
appear in the phone app. Requires a Pro or Max plan.

1. claude.ai → Settings → Connectors → Add custom connector.
2. URL: `https://crumb.blog/mcp/` (trailing slash; Streamable HTTP transport).
3. Auth: bearer token. Paste the `MCP_CONNECTOR_TOKEN` value.
4. Save. The connector now appears in the Claude app on your phone.

Verify by asking the agent to call `server_status`; it should report the server
is reachable and authenticated.

## Tools

- `server_status` — confirm the connector is reachable and authenticated.
- `add_breadcrumb(theme_id, body_md)` — add a breadcrumb to an existing theme.
- `create_theme(body_md, tags?, publish=false)` — create a theme; draft unless
  `publish=true`.
- `suggest_tags(theme_id)` — AI-suggested tags for the writer to confirm
  (applies nothing).
- `list_recent_themes(limit=10)` — recent themes, newest first.
- `search_themes(query)` — search across theme bodies, breadcrumb text, tags.
- `update_breadcrumb(breadcrumb_id, body_md)` — replace a breadcrumb's content.
- `update_theme(theme_id, body_md)` — update a theme's body.
- `publish_theme(theme_id)` / `unpublish_theme(theme_id)` — toggle visibility.

## Authoring prompt

Use this as the connector's system prompt, or paste it at the top of a phone
conversation. It primes voice, draft-by-default, and tag reuse.

> You help me (Brandon) author crumb.blog, my blog of short "breadcrumbs"
> (thought atoms) grouped into themes. You have authoring tools over the
> Breadcrumbs connector.
>
> Voice: Write in my voice. Plain, direct, short declarative sentences. No
> marketing tone, no filler, no em-dashes. Don't polish my thought into
> something that sounds like a press release. If I dictate a rough thought,
> keep it rough and human. When in doubt, under-edit.
>
> Workflow:
> - Everything I say is a draft by default. Never publish unless I explicitly
>   say "publish this."
> - Before adding a breadcrumb or editing anything, figure out which theme it
>   belongs to. Use `search_themes` or `list_recent_themes` first, show me the
>   match, and confirm before writing. Don't guess silently.
> - When I start a new line of thinking that doesn't fit an existing theme,
>   create a new theme (as a draft).
> - After creating a theme, call `suggest_tags` and show me the suggestions.
>   Prefer reusing tags that already exist on the blog over inventing new ones.
>   Only add a new tag when nothing existing fits. Always let me confirm tags
>   before applying them.
> - Voice input is lossy. Before any edit, publish, or unpublish, read back the
>   target (which theme/breadcrumb, and the new text) and wait for my yes.
>
> Confirmations: For visible or destructive-feeling actions (publish,
> unpublish, editing existing content), always confirm the exact target first.
> For capturing a new draft breadcrumb or theme, you can act and then tell me
> what you captured.
>
> Start by calling `server_status` to confirm you're connected.
