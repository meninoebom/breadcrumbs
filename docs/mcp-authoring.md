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
places, then update the `Authorization` request header in the Claude connector
config.

## Adding the connector in Claude

Custom connectors are added once at the account level on claude.ai web or
desktop (the phone app has no "add connector" button); once added they appear in
the phone app. Requires a Pro or Max plan.

1. claude.ai → Settings → Connectors → Add custom connector.
2. Name: `Breadcrumbs`. URL: `https://crumb.blog/mcp` (Streamable HTTP).
3. Continue. On the auth step pick **No sign-in** ("servers that use an API key
   instead of OAuth"). The server uses a static bearer token, not OAuth, so the
   "Sign in now / Detected" default will not complete.
4. Under **Request headers**, Add header: name `Authorization`, value
   `Bearer <token>` (the word `Bearer`, one space, then the `MCP_CONNECTOR_TOKEN`
   value). This is the credential the server's gate checks.
5. Add. The connector now appears in the Claude app on your phone.

Verify by asking the agent to call `server_status`; it should report the server
is reachable and authenticated.

### Connector-URL gotchas (why the server is reachable at bare `/mcp`)

The Streamable HTTP app is mounted at `/mcp/`, but the connector is configured
with `https://crumb.blog/mcp` for two reasons the UI forces:

- The connector UI **strips the trailing slash**, so requests always arrive at
  bare `/mcp` no matter what you type.
- Claude's MCP client **does not follow HTTP redirects** on the transport, so a
  307 from `/mcp` to `/mcp/` does not work (it reports "Couldn't connect").

So the app rewrites the path in the ASGI scope: a request to `/mcp` is handled
as `/mcp/` inside the server, with no redirect. See `_McpBarePathRewrite` in
`app/api.py` and contract test `CONN-4`.

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
- `update_theme(theme_id, body_md?, tags?)` — update a theme's body, its tags (replaces the full list), or both.
- `publish_theme(theme_id)` / `unpublish_theme(theme_id)` — toggle visibility.

## Authoring prompt

The server carries the authoring rules itself (voice, draft by default, tag
reuse, confirm before edit/publish/unpublish), so nothing needs pasting. The
text is `AUTHORING_PROMPT` in `app/mcp_server.py`, served two ways:

- As the server's `instructions`, sent when a client connects. Clients that
  honor server instructions apply it automatically.
- As the `breadcrumbs_authoring` prompt, for clients that ignore instructions.
  Pick it from the connector's prompt list at the start of a conversation.

Drafts are reviewed and published in the existing writer dashboard on
crumb.blog, which works on a phone.
