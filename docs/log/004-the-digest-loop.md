# 004 — The Digest Loop

**Date:** 2026-02-26
**Dimensions:** Architecture, Product Strategy

---

## What Was Built

A complete admin workflow for weekly digests: automated generation via APScheduler, a management UI in the writer dashboard, and a detail drill-down page. The writer can now generate, review, publish, and send digests entirely from the browser — no more curl commands.

## Key Decisions

**APScheduler over Railway Cron.** The app already runs a single web process on Railway. Adding a cron service means another container, another thing to monitor, another deploy. APScheduler runs in-process as a background thread — fewer moving parts for a solo project. The trade-off is that jobs don't run if the app is down, but for weekly summaries that's fine. The idempotency guard (`UNIQUE(period_start)`) means a missed Sunday job just gets picked up on restart.

**Chronological interleaving over separate sections.** The first version put digests in their own section at the bottom of the writer dashboard. You had to scroll past all themes to find them. The fix was obvious once seen: merge themes and digests into one chronological feed, same as the reader view. This also scales naturally to monthly and yearly summaries later — they're just more items in the sorted list.

**`period_end` for positioning.** Digests are sorted by their `period_end` date, not `created_at`. This places them after the content they summarize, which makes chronological sense. A small detail that took thought to get right in the reader feed and was worth reusing exactly in the writer feed.

## What Surprised Me

The "generate early" problem: if you generate a digest on Wednesday, the Sunday cron sees it already exists and skips. Any themes added Thursday–Sunday are missed. The fix (regeneration) is scoped but not yet built. It's a good example of how automation surfaces edge cases that manual workflows hide.

## The Takeaway

Admin UIs for AI features matter more than they seem. Without the digest management page, the whole review-before-publish workflow was API-only — technically possible but practically unused. Making it visible in the dashboard turns it from "a thing the system does" into "a thing I actively manage." The feature isn't really shipped until a human can comfortably use it.
