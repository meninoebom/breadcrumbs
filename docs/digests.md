# Digests (Weekly & Monthly Summaries)

**What:** AI-generated summaries that appear inline in the main feed, interleaved chronologically with regular breadcrumbs. Weekly summaries (2-4 sentences) recap the week's themes. Monthly summaries (3-6 sentences) synthesize weekly summaries into higher-altitude arcs via progressive summarization.

## Architecture
- `app/digest/` -- Generation (Claude), email (Resend), sending, API routes
- Models: `Digest`, `DigestType`, `Subscriber`, `DigestSend` (in `app/models.py`)
- `DigestType` enum: `weekly` or `monthly` -- stored on the `Digest` model
- Frontend: summaries render inline via `WeeklySummary` component in the main feed
- Writer dashboard: digests interleaved chronologically with themes, clickable detail page at `/writer/digests/$digestId`
- Confirm/unsubscribe pages: `/digest/confirm`, `/digest/unsubscribe`
- Scheduler: `app/scheduler.py` -- APScheduler `BackgroundScheduler` with three cron jobs
- AI indicator: subtle sparkles icon (lucide-react) in bottom-right of every summary card, with "AI-generated summary" tooltip

## How summaries appear in the feed
- The feed merges date-grouped themes and published digests into one chronological list
- Summaries are keyed by `period_end` date, so they appear after that period's content
- Different visual treatment: dashed border, muted background, lighter heading
- Monthly headings show "February 2026", weekly show "Week of Feb 1-7, 2026"
- Summaries are hidden when tag/search filters are active

## Progressive summarization
- Weekly digests summarize raw themes + breadcrumbs
- Monthly digests summarize published weekly digests (not raw content)
- Fallback: if no weekly digests exist for a month, falls back to raw content
- This creates a pyramid of abstraction: weekly captures details, monthly captures trends
- Future: yearly summaries from monthly summaries

## Admin workflow (manual or agent)
1. `POST /api/digests/generate?period_start=YYYY-MM-DD&period_end=YYYY-MM-DD&digest_type=weekly` -- Claude writes a summary (draft)
2. `POST /api/digests/generate?digest_type=monthly` -- generates monthly from weekly summaries (auto-detects previous month bounds)
3. `POST /api/digests/{id}/publish` -- Makes it visible in the feed
4. `POST /api/digests/{id}/send` -- (Optional) deliver to email subscribers

## Scheduler (APScheduler)
- In-process `BackgroundScheduler` in `app/scheduler.py`, gated behind `ENABLE_SCHEDULER=true`
- Sunday 6am PT (14:00 UTC): generates a draft weekly digest for the past week
- 1st of month 6am PT (14:00 UTC): generates a draft monthly digest for the previous month
- Tuesday 6am PT (14:00 UTC): publishes and sends any draft digests (weekly or monthly)
- Idempotent: checks for existing digest with same `period_start` + `digest_type` before generating
- Each job creates its own `Session(engine)` since it runs outside request context
- **Known limitation:** generating early in the week/month then generating again later does NOT update the draft -- it skips because one already exists. Regeneration not yet implemented.

## Legacy cron endpoint (still available)
`POST /api/internal/weekly-digest?secret=X&auto_send=true`
- Needs `CRON_SECRET` env var set
- Superseded by APScheduler but kept for manual triggering

## Email subscriptions (modular, can be removed)
- Subscribe widget at bottom of feed with double opt-in flow
- Resend for delivery (RESEND_API_KEY env var)
- Emails contain the short summary + link to homepage
- Subscriber flow is fully independent of summary display

## Key constraints
- `UNIQUE(period_start, digest_type)` on digest -- prevents duplicate digests per period and type
- `UNIQUE(digest_id, subscriber_id)` on digest_send -- prevents double-sending
- Indexes on `confirmation_token` and `unsubscribe_token` for fast lookups

## Generation prompts
Live in `app/digest/generate.py`. Weekly: `SYSTEM_PROMPT` (journalist capsule recap). Monthly: `MONTHLY_SYSTEM_PROMPT` (magazine month-in-review). Both third-person, warm, observational.

## Future direction
Yearly summaries from monthly summaries. Digest regeneration for updating drafts.
