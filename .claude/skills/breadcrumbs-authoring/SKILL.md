# Breadcrumbs Authoring

Write and publish content on [crumb.blog](https://crumb.blog) — a blog of collected thought atoms organized into themes.

## When to Use

- User wants to capture a thought, observation, or connection as a theme
- User wants to add a sub-thought (breadcrumb) to an existing theme
- User provides raw notes, voice memos, or ideas to be shaped into breadcrumbs
- User says "post to crumb.blog", "write a breadcrumb", "new theme", or similar

## Inspiration

This blog is inspired by Alex Komoroske's ["Bits and Bobs"](https://docs.google.com/document/d/1GrEFrdF_IzRVXbGH1lG0aQMlvsB71XihPPqQN-ONTuo/edit) — a 600+ page running Google Doc of small, interconnected thoughts. Komoroske captures raw notes during the week, then reflects weekly to find patterns and distill insights. Breadcrumbs is the structured, web-native version of that practice.

Brandon's voice is his own — not Komoroske's. The format is the inspiration, not the tone.

## Content Structure

### Theme (the primary unit)

A theme is a captured thought — an observation, connection, provocation, or question. **Not** an article. **Not** a blog post. Think: one idea that could spark a conversation.

- **Length:** 1-5 sentences. Brevity is a feature.
- **Format:** Markdown (links, emphasis, block quotes all welcome)
- **Tags:** 1-5 per theme. How readers discover and navigate content.
- **Visibility:** Starts as `draft`, publish when ready.

### Breadcrumb (sub-thought)

A breadcrumb elaborates on, replies to, or branches off from a theme. It's the "yes, and..." or "but what about..." that follows.

- **Length:** 1-3 sentences.
- **Nesting:** Breadcrumbs can reply to other breadcrumbs (max depth 10).
- **Belongs to exactly one theme.** Cannot exist independently.

### Tags (discovery handles)

- Lowercase, dash-separated (e.g., `mental-models`, `ai`, `john-vervaeke`)
- API auto-normalizes: whitespace becomes dashes, strips leading/trailing dashes
- **Prefer reusing existing tags** over creating new ones. Check `GET /api/tags` first.
- 1-5 tags per theme. Tags are applied at the theme level, not breadcrumbs.

## Voice & Tone

The voice is still developing. Current patterns from the blog:

- **Direct over decorative.** Say the thing, don't wrap it in preamble.
- **Insight over information.** Not "here's a fact" but "here's a connection I noticed."
- **Questions are welcome.** A theme can end with a question mark.
- **Personal experience is valid.** "I noticed..." and "I experienced..." are fine.
- **Compressed is good.** If it can be one sentence, make it one sentence.
- **Markdown links to sources** when referencing someone else's idea.

## Examples (from crumb.blog)

**Philosophical / provocative:**
> Current AI — LLMs, transformers — is what you get when you take the Cartesian worldview as far as it can possibly go. Descartes split mind from body, declared the universe a mechanism, and dreamed of a universal mathematics underlying all knowledge. Three centuries later, we built it: disembodied cognition running on matrix multiplication, processing all of human language without ever having touched anything. The question is whether this is a triumph or a reductio ad absurdum.
>
> *tags: ai, philosophy, descartes*

**Compressed insight:**
> Agentic AI works best at the edges of the gradient of your competence, not beyond them.
>
> *tags: mental-models, ai, creative-coding*

**Observational / personal:**
> I experienced the power of open-minded collaboration at Dance Hack this weekend.
>
> *tags: collaboration, dance-hack, dance, motion-capture*

**Meta / compounding:**
> A compounding cycle is emerging for me with agentic coding tools: have them build tools that teach me concepts that I build better tools.
>
> *tags: ai, claude-code, software*

**Referencing a source:**
> Diana Winston's framework of [the spectrum of awareness](https://www.youtube.com/watch?v=1kumYldDZ38) helped me bridge what felt like a divide between insight meditation (vipassana) and non-dual practice.
>
> *tags: meditation, non-dualism, vipassana*

## API Reference

**Base URLs:**
- Production: `https://crumb.blog`
- Development: `http://localhost:8000`

### Authenticate

```
POST /api/auth/login
Body: {"password": "<ADMIN_PASSWORD>"}
Response: {"access_token": "<jwt_token>"}
```

Use the token as `Authorization: Bearer <jwt_token>` on all mutating requests.

### Create a Theme

```
POST /api/themes
Headers: Authorization: Bearer <token>
Body: {
  "body_md": "The thought in markdown.",
  "tags": [{"name": "tag-one"}, {"name": "tag-two"}],
  "visibility": "draft"
}
Response: 201 with ThemePublic (id, body_md, visibility, tags, created_at)
```

### Add a Breadcrumb

```
POST /api/themes/{theme_id}/breadcrumbs
Headers: Authorization: Bearer <token>
Body: {
  "body_md": "The sub-thought in markdown.",
  "parent_id": null
}
Response: 201 with BreadcrumbPublic
```

Set `parent_id` to another breadcrumb's ID to nest (reply to a breadcrumb).

### Publish a Theme

```
PUT /api/themes/{theme_id}
Headers: Authorization: Bearer <token>
Body: {"visibility": "published"}
Response: 200 with updated ThemePublic
```

### List Existing Tags

```
GET /api/tags
Response: [{"id": 1, "name": "ai"}, ...]
```

Check this before creating themes to reuse existing tags.

## Content Workflow

1. **Draft** — Create the theme with `visibility: "draft"`. Review it.
2. **Add breadcrumbs** — Optionally add sub-thoughts to flesh out the theme.
3. **Publish** — Set `visibility: "published"` when ready. It appears in the reader stream immediately.
4. **Digest** — Published themes automatically feed into the weekly AI-generated digest (no action needed).

### When shaping raw input

If the user provides rough notes, voice memo transcripts, or stream-of-consciousness text:

1. Identify distinct thoughts — each becomes a candidate theme
2. Compress to the essential insight (1-5 sentences)
3. Suggest tags from existing tags where possible
4. Present the shaped themes for approval before posting
5. Default to `draft` visibility — let the user decide when to publish

## Deployment

The blog runs on **Railway** with auto-deploy from the `main` branch.

- Content creation is purely API calls — no deployment needed
- For deployment operations (code changes, migrations), use the `railway:deploy` skill
- Environment variables (`ADMIN_PASSWORD`, `JWT_SECRET`, etc.) are set in Railway
