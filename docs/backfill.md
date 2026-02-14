# Production Backfill Document

Source of truth for populating the crumb.blog production database.
Review, edit, then use to script API calls against the production endpoint.

**Sources harvested:**
- Local Breadcrumbs Postgres (5 themes, 16 breadcrumbs)
- Breadcrumbs `docs/log/` (3 entries)
- Tend `docs/log/` (5 entries)
- Huddle `docs/log/` (4 entries)

---

## Part 1: Existing Local DB Content

These are already in the local database. Include in production backfill as-is.

---

### Theme: Musicality is social contemplative practice.
**Tags:** music, contemplative-practices, dance, meditation
**Visibility:** published

1. It is a kind of embodied discourse on the fundamental unity of all awareness.

---

### Theme: The Past and Future are Ghosts
**Tags:** fear, presence
**Visibility:** published

1. The past and future are ghosts that haunt us until we stop running from them, face them, try to touch them, and then see that they are imagined and unreal.
2. As with monsters in dreams, when we become lucid we realize the unreality of the past and future.
3. Courage in a dream comes immediately upon realizing it's a dream.
4. Courage in the "waking state" comes immediately upon realizing it's a dream.

---

### Theme: Attention
**Tags:** awareness, contemplative-practices, meditation, non-dualism
**Visibility:** published

1. Try allowing your attention to flow downhill toward whatever is calling it. Withdraw all effort from controlling your attention and allow it to chase every fleeting experience that attracts it.
2. This is described like walking a dog and allowing it to sniff whatever grabs its interest.
3. The effect is that if you do this mindfully, you begin to notice the difference between attention and awareness.

---

### Theme: The follow-up prompt is under-appreciated
**Tags:** ai, claude-code
**Visibility:** published

1. Without it I would have to often reorient myself to the thread by re-reading previous conversation.
2. Just finding where to start re-reading has a high cognitive cost.
3. These contextual bookmarks make switching multiple agents much easier.
4. Claude claims that the follow-up prompt suggestion "removes 3-5 micro-decisions per workflow."

---

### Theme: Bernardo Kastrup dropped some gems on [this podcast](https://edgeofmindpodcast.com/bernardo-kastrup-part-ii-the-nature-of-reality/)
**Tags:** philosophy-of-mind, bernardo-kastrup, death
**Visibility:** published

1. "A healthy life is one that ends at the right time — and in the right way."
2. "Healing is what always happens when we are not busy doing something else."
3. Active mental states "appear" in the body (brain). But memories do not seem to appear there.

---

## Part 2: Harvested from Project Logs

New content extracted from learning journals. Each log entry becomes a theme; key insights become breadcrumbs.

---

### Theme: A prototype is worth a thousand meetings
**Tags:** prototyping, process, ai
**Visibility:** published
**Source:** Breadcrumbs log 001 (2026-02-09)

1. The bottleneck used to be "can we build it?" Now it's "are we building the right thing?"
2. When prototyping is this cheap and this fast, the cost of being wrong about a design choice approaches zero — you can build it, see it, hate it, and rebuild it faster than you can schedule a meeting to debate whether it's the right approach.
3. The question isn't whether you *can* build four features in a session. It's whether those four features are the right ones. And the fastest way to answer that is to put them in front of someone.

---

### Theme: Clay, not blueprints
**Tags:** software-as-clay, ai, product-design
**Visibility:** published
**Source:** Breadcrumbs log 002 (2026-02-09)

1. Traditional software development is like designing a building — deviation during construction is costly and dangerous. Agentic engineering is more like forming clay. There's more leeway, more play. It's forgiving.
2. The format draws out a kind of thinking — iterative, playful, brainstorm-shaped. Not depth but ideation. You mine your own experience for what matters, and the ideas that want depth reveal themselves.
3. A major architectural decision reversed cleanly because the cost of being wrong was just another session. The code bent. Nothing broke.
4. I'm not designing a product and then building it. I'm prototyping to discover what the product wants to be. The agent makes that loop tight enough that the prototype *is* the thinking tool.

---

### Theme: Building software is like molding clay.
**Tags:** software-as-clay, ai, input-output-systems
**Visibility:** published
**Source:** Breadcrumbs log 003 (2026-02-12)

1. As long as the material is shaped such that it is structurally sound, the possibilities are vast and the material is very forgiving.
2. With agents, the reshaping speed is fast enough that you can think *through* the material rather than *about* it.
3. Breadcrumbs started as a blog. It's becoming an input/output system for my thinking. The blog is one output surface. Voice is one input surface. The breadcrumbs themselves are the substrate — small, atomic, accretive. Each one makes the system a little smarter about who I am.

---

### Theme: You need speed bumps when code is cheap
**Tags:** process, ai, reflection
**Visibility:** published
**Source:** Tend log 001 (2026-02-08)

1. The cost of code is so low that the dangers come in the form of having too much code — or not enough friction to think clearly about your outcomes and your customers.
2. You need speed bumps when you can produce so much code so quickly, to force yourself to do some of the planning and reflection that you used to have to do by virtue of the cost of producing code.
3. Schema-first sequencing pays off: because there was already a PATCH endpoint, adding UI richness — inline editing — was straightforward. That's the payoff of investing in the foundation first.
4. Product instinct is at the edge of my skill set. Building a product isn't just code — it's the decisions about what to build next, and the honesty to say when you're guessing.

---

### Theme: Every state the user can reach in the UI should have a corresponding API call that works.
**Tags:** backend, api-design, python
**Visibility:** published
**Source:** Tend log 002 (2026-02-08)

1. In any PATCH endpoint where fields are optional AND nullable, `None` can mean "clear this field" or "don't touch it." The sentinel pattern replaces the default with a unique object that can't be confused with any real value.

---

### Theme: Avoid premature optimization of your workflow
**Tags:** process, ai, workflow
**Visibility:** published
**Source:** Tend log 003 (2026-02-08)

1. The cost of spinning up parallel work streams is so low that it feels free. But the coordination cost — keeping your mental model coherent across multiple branches, resolving conflicts, ensuring features compose correctly — is not free.
2. It's the same trap as premature code optimization: you're spending effort on speed before you know where the bottleneck is.
3. For now, sequential is fine. One branch, one feature, one PR. When the project gets complex enough that I'm genuinely blocked waiting for builds or reviews, *then* parallelize.

---

### Theme: Dogfooding, emotional attachment, and Christopher Alexander
**Tags:** product-design, ux, dogfooding, christopher-alexander
**Visibility:** published
**Source:** Tend log 004 (2026-02-09)

1. Dogfooding works. I would not have found this bug without actually using the app.
2. Discovered a bug with a cycling button state interaction.
3. Seemed perfectly fine in isolation. It was only when I was in a filtered domain that the problem became obvious.
4. I was emotionally attached to the simplicity of the cycling button, and that attachment was pulling me toward complicated workarounds to preserve it. I had to let go of that.

---

### Theme: Now that prototyping costs have plummeted, we can build software the way Christopher Alexander talked about building architecture: through close listening to the people who are going to live in a space.
**Tags:** ai, design, process
**Visibility:** published
**Source:** Tend log 005 (2026-02-09)

1. If you can go from idea to working UI in a day, you can build, watch, listen, and rebuild — letting the design form itself to real needs rather than imagined ones.

---

### Theme: Agent-driven design is like throwing pots.
**Tags:** software-as-clay, ai, design
**Visibility:** published

1. The product feels not-broken. It's a bowl on the potter's wheel.
2. Development in this metaphor is a continuous process of making small improvements to manifest a unique object reflecting human intention.
3. Prompting changes is pushing your metaphorical fingers into the spinning clay.

---

### Theme: To me "resonant computing" means remove the parts that feel like work to make room for the parts that feel like connection.
**Tags:** ai, product-design, resonant-computing
**Visibility:** published
**Source:** Huddle log 001 (2026-02-09)

---

### Theme: Maybe evals are the new design mocks
**Tags:** ai, evals, conversational-ux
**Visibility:** published
**Source:** Huddle log 004 (2026-02-11)

1. Maybe for an agentic product, the eval suite *is* the design spec. "When someone says 'let's meet this weekend,' the bot should create a session and reply with something that collects availability" — that's simultaneously a test case and a design decision.

---

### Theme: APIs are commodities now.
**Tags:** ai, backend
**Visibility:** published

---

### Theme: Are there properties from improvisational music traditions that apply to conversational interfaces? Rhythm, indeterminacy, structure, shared vocabulary.
**Tags:** improvisation, music, conversational-ux
**Visibility:** published

1. The drum circle and the group text are both coordination protocols for small groups with no central authority.
