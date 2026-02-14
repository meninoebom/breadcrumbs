"""
Backfill production database from docs/backfill.md content.

Usage:
    python scripts/backfill.py                    # dry run (prints what would be created)
    python scripts/backfill.py --execute          # actually POST to production
    python scripts/backfill.py --execute --url http://localhost:8000  # target local
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

BASE_URL = "https://crumb.blog"

THEMES = [
    # --- Part 1: Existing Local DB Content ---
    {
        "body_md": "Musicality is social contemplative practice.",
        "tags": ["music", "contemplative-practices", "dance", "meditation"],
        "breadcrumbs": [
            "It is a kind of embodied discourse on the fundamental unity of all awareness.",
        ],
    },
    {
        "body_md": "The Past and Future are Ghosts",
        "tags": ["fear", "presence"],
        "breadcrumbs": [
            "The past and future are ghosts that haunt us until we stop running from them, face them, try to touch them, and then see that they are imagined and unreal.",
            "As with monsters in dreams, when we become lucid we realize the unreality of the past and future.",
            "Courage in a dream comes immediately upon realizing it's a dream.",
            'Courage in the "waking state" comes immediately upon realizing it\'s a dream.',
        ],
    },
    {
        "body_md": "Attention",
        "tags": ["awareness", "contemplative-practices", "meditation", "non-dualism"],
        "breadcrumbs": [
            "Try allowing your attention to flow downhill toward whatever is calling it. Withdraw all effort from controlling your attention and allow it to chase every fleeting experience that attracts it.",
            "This is described like walking a dog and allowing it to sniff whatever grabs its interest.",
            "The effect is that if you do this mindfully, you begin to notice the difference between attention and awareness.",
        ],
    },
    {
        "body_md": "The follow-up prompt is under-appreciated",
        "tags": ["ai", "claude-code"],
        "breadcrumbs": [
            "Without it I would have to often reorient myself to the thread by re-reading previous conversation.",
            "Just finding where to start re-reading has a high cognitive cost.",
            "These contextual bookmarks make switching multiple agents much easier.",
            'Claude claims that the follow-up prompt suggestion "removes 3-5 micro-decisions per workflow."',
        ],
    },
    {
        "body_md": "Bernardo Kastrup dropped some gems on [this podcast](https://edgeofmindpodcast.com/bernardo-kastrup-part-ii-the-nature-of-reality/)",
        "tags": ["philosophy-of-mind", "bernardo-kastrup", "death"],
        "breadcrumbs": [
            '"A healthy life is one that ends at the right time \u2014 and in the right way."',
            '"Healing is what always happens when we are not busy doing something else."',
            'Active mental states "appear" in the body (brain). But memories do not seem to appear there.',
        ],
    },
    # --- Part 2: Harvested from Project Logs ---
    {
        "body_md": "A prototype is worth a thousand meetings",
        "tags": ["prototyping", "process", "ai"],
        "breadcrumbs": [
            'The bottleneck used to be "can we build it?" Now it\'s "are we building the right thing?"',
            "When prototyping is this cheap and this fast, the cost of being wrong about a design choice approaches zero \u2014 you can build it, see it, hate it, and rebuild it faster than you can schedule a meeting to debate whether it's the right approach.",
            "The question isn't whether you *can* build four features in a session. It's whether those four features are the right ones. And the fastest way to answer that is to put them in front of someone.",
        ],
    },
    {
        "body_md": "Clay, not blueprints",
        "tags": ["software-as-clay", "ai", "product-design"],
        "breadcrumbs": [
            "Traditional software development is like designing a building \u2014 deviation during construction is costly and dangerous. Agentic engineering is more like forming clay. There's more leeway, more play. It's forgiving.",
            "The format draws out a kind of thinking \u2014 iterative, playful, brainstorm-shaped. Not depth but ideation. You mine your own experience for what matters, and the ideas that want depth reveal themselves.",
            "A major architectural decision reversed cleanly because the cost of being wrong was just another session. The code bent. Nothing broke.",
            "I'm not designing a product and then building it. I'm prototyping to discover what the product wants to be. The agent makes that loop tight enough that the prototype *is* the thinking tool.",
        ],
    },
    {
        "body_md": "Building software is like molding clay.",
        "tags": ["software-as-clay", "ai", "input-output-systems"],
        "breadcrumbs": [
            "As long as the material is shaped such that it is structurally sound, the possibilities are vast and the material is very forgiving.",
            "With agents, the reshaping speed is fast enough that you can think *through* the material rather than *about* it.",
            "Breadcrumbs started as a blog. It's becoming an input/output system for my thinking. The blog is one output surface. Voice is one input surface. The breadcrumbs themselves are the substrate \u2014 small, atomic, accretive. Each one makes the system a little smarter about who I am.",
        ],
    },
    {
        "body_md": "You need speed bumps when code is cheap",
        "tags": ["process", "ai", "reflection"],
        "breadcrumbs": [
            "The cost of code is so low that the dangers come in the form of having too much code \u2014 or not enough friction to think clearly about your outcomes and your customers.",
            "You need speed bumps when you can produce so much code so quickly, to force yourself to do some of the planning and reflection that you used to have to do by virtue of the cost of producing code.",
            "Schema-first sequencing pays off: because there was already a PATCH endpoint, adding UI richness \u2014 inline editing \u2014 was straightforward. That's the payoff of investing in the foundation first.",
            "Product instinct is at the edge of my skill set. Building a product isn't just code \u2014 it's the decisions about what to build next, and the honesty to say when you're guessing.",
        ],
    },
    {
        "body_md": "Every state the user can reach in the UI should have a corresponding API call that works.",
        "tags": ["backend", "api-design", "python"],
        "breadcrumbs": [
            'In any PATCH endpoint where fields are optional AND nullable, `None` can mean "clear this field" or "don\'t touch it." The sentinel pattern replaces the default with a unique object that can\'t be confused with any real value.',
        ],
    },
    {
        "body_md": "Avoid premature optimization of your workflow",
        "tags": ["process", "ai", "workflow"],
        "breadcrumbs": [
            "The cost of spinning up parallel work streams is so low that it feels free. But the coordination cost \u2014 keeping your mental model coherent across multiple branches, resolving conflicts, ensuring features compose correctly \u2014 is not free.",
            "It's the same trap as premature code optimization: you're spending effort on speed before you know where the bottleneck is.",
            "For now, sequential is fine. One branch, one feature, one PR. When the project gets complex enough that I'm genuinely blocked waiting for builds or reviews, *then* parallelize.",
        ],
    },
    {
        "body_md": "Dogfooding, emotional attachment, and Christopher Alexander",
        "tags": ["product-design", "ux", "dogfooding", "christopher-alexander"],
        "breadcrumbs": [
            "Dogfooding works. I would not have found this bug without actually using the app.",
            "Discovered a bug with a cycling button state interaction.",
            "Seemed perfectly fine in isolation. It was only when I was in a filtered domain that the problem became obvious.",
            "I was emotionally attached to the simplicity of the cycling button, and that attachment was pulling me toward complicated workarounds to preserve it. I had to let go of that.",
        ],
    },
    {
        "body_md": "Now that prototyping costs have plummeted, we can build software the way Christopher Alexander talked about building architecture: through close listening to the people who are going to live in a space.",
        "tags": ["ai", "design", "process"],
        "breadcrumbs": [
            "If you can go from idea to working UI in a day, you can build, watch, listen, and rebuild \u2014 letting the design form itself to real needs rather than imagined ones.",
        ],
    },
    {
        "body_md": "Agent-driven design is like throwing pots.",
        "tags": ["software-as-clay", "ai", "design"],
        "breadcrumbs": [
            "The product feels not-broken. It's a bowl on the potter's wheel.",
            "Development in this metaphor is a continuous process of making small improvements to manifest a unique object reflecting human intention.",
            "Prompting changes is pushing your metaphorical fingers into the spinning clay.",
        ],
    },
    {
        "body_md": 'To me "resonant computing" means remove the parts that feel like work to make room for the parts that feel like connection.',
        "tags": ["ai", "product-design", "resonant-computing"],
        "breadcrumbs": [],
    },
    {
        "body_md": "Maybe evals are the new design mocks",
        "tags": ["ai", "evals", "conversational-ux"],
        "breadcrumbs": [
            'Maybe for an agentic product, the eval suite *is* the design spec. "When someone says \'let\'s meet this weekend,\' the bot should create a session and reply with something that collects availability" \u2014 that\'s simultaneously a test case and a design decision.',
        ],
    },
    {
        "body_md": "APIs are commodities now.",
        "tags": ["ai", "backend"],
        "breadcrumbs": [],
    },
    {
        "body_md": "Are there properties from improvisational music traditions that apply to conversational interfaces? Rhythm, indeterminacy, structure, shared vocabulary.",
        "tags": ["improvisation", "music", "conversational-ux"],
        "breadcrumbs": [
            "The drum circle and the group text are both coordination protocols for small groups with no central authority.",
        ],
    },
]


def post_json(url: str, data: dict) -> dict:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Backfill Breadcrumbs production DB")
    parser.add_argument("--execute", action="store_true", help="Actually run the backfill (default is dry run)")
    parser.add_argument("--url", default=BASE_URL, help=f"Base URL (default: {BASE_URL})")
    args = parser.parse_args()

    total_themes = len(THEMES)
    total_crumbs = sum(len(t["breadcrumbs"]) for t in THEMES)

    if not args.execute:
        print(f"DRY RUN: would create {total_themes} themes and {total_crumbs} breadcrumbs")
        print(f"Target: {args.url}")
        print()
        for i, theme in enumerate(THEMES, 1):
            print(f"  {i}. {theme['body_md'][:70]}...")
            print(f"     Tags: {', '.join(theme['tags'])}")
            print(f"     Breadcrumbs: {len(theme['breadcrumbs'])}")
        print()
        print("Run with --execute to perform the backfill.")
        return

    print(f"Backfilling {total_themes} themes and {total_crumbs} breadcrumbs to {args.url}")
    print()

    created_themes = 0
    created_crumbs = 0
    errors = []

    for i, theme_data in enumerate(THEMES, 1):
        theme_payload = {
            "body_md": theme_data["body_md"],
            "visibility": "published",
            "tags": [{"name": t} for t in theme_data["tags"]],
        }

        try:
            result = post_json(f"{args.url}/api/themes", theme_payload)
            theme_id = result["id"]
            created_themes += 1
            print(f"  [{i}/{total_themes}] Created theme {theme_id}: {theme_data['body_md'][:60]}...")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            errors.append(f"Theme {i}: {e.code} {error_body}")
            print(f"  [{i}/{total_themes}] FAILED: {e.code} {error_body}")
            continue

        for j, crumb_text in enumerate(theme_data["breadcrumbs"], 1):
            crumb_payload = {"body_md": crumb_text}
            try:
                post_json(f"{args.url}/api/themes/{theme_id}/breadcrumbs", crumb_payload)
                created_crumbs += 1
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                errors.append(f"Theme {theme_id}, crumb {j}: {e.code} {error_body}")
                print(f"    FAILED crumb {j}: {e.code} {error_body}")

    print()
    print(f"Done: {created_themes}/{total_themes} themes, {created_crumbs}/{total_crumbs} breadcrumbs")
    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
