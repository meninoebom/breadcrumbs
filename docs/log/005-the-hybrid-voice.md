# 005 — The Hybrid Voice

**Date:** 2026-02-28
**Dimensions:** Product Strategy, Process & Tooling

---

## What Was Built

Monthly digest generation via progressive summarization (weekly summaries become input for monthly summaries), and a subtle AI-generated indicator — a faded sparkles icon in the corner of every summary card.

## The Real Experiment

This feature made something concrete that had been abstract: Breadcrumbs is becoming a hybrid human-computer product. My writing goes in as raw thought atoms. An AI model reads them, compresses them, and presents them back — first as weekly recaps, now as monthly arcs. The sparkles icon is a small act of transparency about that process.

What's interesting is the question it raises: how does it feel to have your own ideas reflected back through the filter of a language model? Not someone else's ideas summarized — *your own*, repackaged in a voice that isn't quite yours. It's a different relationship than using AI as a coding assistant or a search tool. This is AI as a collaborator in self-expression, which is a weirder and more personal territory.

## What I'm Watching For

**Builder side:** Does the progressive summarization pipeline (weekly to monthly to eventually yearly) produce something that feels insightful, or does it flatten the texture of the original writing? Lossy compression on top of lossy compression could converge on bland. The monthly prompt asks for "threads and arcs" rather than topic lists — that's a bet that higher-altitude summaries should be more reflective, not just shorter.

**Reader side:** When someone reads a monthly summary of my thinking, are they reading *me*? Or are they reading Claude's interpretation of me? The sparkles icon gestures at this ambiguity without resolving it. That feels honest.

**The product question:** There's a category of product emerging that's neither fully human-authored nor fully AI-generated — it's a hybrid where human intent passes through computational mediation. Breadcrumbs is a small experiment in what that feels like to build and to read.

## Technical Note

The monthly generation queries published weekly digests rather than raw content. This is faster and cheaper, but the real reason is conceptual: monthly summaries should operate at a different altitude than weekly ones. They're summaries of summaries — pattern recognition on pattern recognition. If a weekly summary missed something, the monthly will too. That's an acceptable trade-off for now; the fallback to raw content exists for months with no weekly digests.
