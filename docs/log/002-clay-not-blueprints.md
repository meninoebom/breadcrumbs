# 002 — Clay, Not Blueprints

**Date:** 2026-02-09
**Dimensions:** Product Strategy, UX Design

---

## What happened

I planned to remove the Breadcrumb model entirely — simplify the data model, merge everything into themes. Three review agents agreed. Then a devil's advocate reviewer made the case for keeping breadcrumbs: per-thought timestamps, rapid-fire capture, structured data for future agents. That landed. Not only did the breadcrumbs stay, the model grew — I added parent-child relationships so breadcrumbs can nest. A complete reversal, in one session.

## The real question

I'm building Breadcrumbs because I saw something in Alex Komoroske's "Bits and Bobs" Google Doc that I wanted for myself. But when I started, I couldn't articulate *what* makes his approach work. What are the affordances? What features produce the utility?

It's something about pith. The format draws out a kind of thinking — iterative, playful, brainstorm-shaped. Not depth but ideation. You mine your own experience for what matters, and then the ideas that want depth reveal themselves. You don't plan the depth in advance; it emerges from the play.

## The analogy

Traditional software development is like designing a building. You figure out your parameters, produce a precise plan, and deviation during construction is costly and dangerous.

What I'm finding with agentic engineering is more like forming clay. There's more leeway, more play. It's forgiving. I can build a prototype, live in it, feel what's wrong, reshape it — and the cost of that reshaping approaches zero.

This session proved it: a major architectural decision (remove vs. keep vs. extend breadcrumbs) reversed cleanly because the cost of being wrong was just... another session. The code bent. Nothing broke.

## The takeaway

I'm not designing a product and then building it. I'm prototyping to discover what the product wants to be. The agent makes that loop tight enough that the prototype *is* the thinking tool. Each build is a question: does this form factor promote the kind of thinking I'm after? And I can answer it by touching the clay, not by staring at blueprints.
