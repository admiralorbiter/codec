# Codec — Research Basis & Long-Term Roadmap

## 1. Why this is not just another project manager

Codec sits at the intersection of several research traditions that rarely meet in one product:

- activity-centric computing;
- interruption and task-resumption research;
- prospective memory and implementation intentions;
- cognitive offloading;
- human–AI delegation and metacognition;
- knowledge/provenance graphs;
- mixed-initiative interfaces;
- asynchronous agent/computation orchestration;
- work–life boundary management.

The historical activity-centric question was roughly:

> What activity is the human working on, and what resources belong to it?

Codec's AI-era extension is:

> **What activity is underway across the human, agents, tools, and external world; where is its frontier; what can continue without the human; and what form of human cognition does it require next?**

That is the long-term research thesis.

## 2. Research findings that directly change V0

### 2.1 Re-entry cues are core, not decorative

Developer-interruption research found that resumption involves reconstructing conceptual context and that automated contextual cues can improve resumption. Parnin & Rugaber surveyed 371 programmers and experimentally compared resumption cues with ordinary note-taking.

**Codec implication:** Park / Resume is a primary product loop. Frontier, stopping reason, next action, and relevant surfaces deserve first-class treatment.

Sources:
- https://www.microsoft.com/en-us/research/publication/evaluating-cues-for-resuming-interrupted-programming-tasks/
- https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/CHI_2007_Iqbal_Horvitz-1.pdf

### 2.2 Activity should organize resources across applications

TaskTracer and activity-centric computing research attempted to organize files, applications, and information around ongoing human activities rather than around application silos.

**Codec implication:** a thread can contain ChatGPT, Antigravity, GitHub, local files, audio, browser sources, and notebook artifacts without treating each application as a separate project.

Sources:
- https://dl.acm.org/doi/10.1145/1040830.1040855
- https://pure.itu.dk/en/publications/activity-centric-computing-systems/

### 2.3 Waiting should encode a cue and action

Implementation-intention research studies plans of the general form **if X, then Y** and their role in goal pursuit and prospective memory.

**Codec implication:** `WAITING` should usually have a `resume_condition` and `next_action`, not just a passive status.

Example:

> When the Pathful export arrives → run validation.

Source:
- https://www.annualreviews.org/content/journals/10.1146/annurev-psych-021524-110536

### 2.4 Goals deserve a durable place without creating bureaucracy

A 2026 Microsoft Research position paper argues for goals as first-class abstractions in human–AI collaboration, particularly because implementations, artifacts, and agents can change while goals persist.

**Codec implication:** preserve natural-language intent from V0, but do not force a heavyweight goals hierarchy. Promote Goal to a graph object only after actual use demonstrates value.

Source:
- https://www.microsoft.com/en-us/research/publication/goals-as-first-class-abstractions-in-human-ai-collaboration/

### 2.5 AI creates coordination/metacognitive work

Human–AI work requires decisions about delegation, verification, prompting, trust, and intervention. Recent research frames these as metacognitive demands rather than assuming AI assistance is cognitively free.

**Codec implication:** agent management must reduce coordination load. A running agent is not automatically progress if it generates more unstructured things to verify.

Sources:
- https://www.microsoft.com/en-us/research/project/tools-for-thought/publications/
- https://www.microsoft.com/en-us/research/people/advait/publications/

### 2.6 Eliminate mundane articulation; preserve productive articulation

Larsen-Ledet distinguishes productive articulation—clarifying the actual work—from mundane articulation—repeatedly restating setup/context so AI can function.

**Codec implication:** context packets should carry stable project/thread knowledge to AI surfaces while still requiring the user to articulate genuinely new goals and judgments.

Source:
- https://research.ucc.ie/en/publications/generative-ai-at-work-mundane-and-productive-articulation/

### 2.7 Progressive disclosure is appropriate for AI-heavy interfaces

Google PAIR recommends building usable mental models, feedback/control loops, and progressive disclosure of deeper explanations instead of dumping model complexity into the primary interface.

**Codec implication:** compact thread cards first; detailed provenance, logs, explanations, and graph relations on demand.

Sources:
- https://pair.withgoogle.com/chapter/mental-models/
- https://pair.withgoogle.com/guidebook/chapters/trust-and-explanations/crafting-helpful-explanations
- https://pair.withgoogle.com/guidebook/chapters/feedback-and-controls/design-ai-feedback-loops

### 2.8 Timing matters for interruptions

Research on opportune moments for transitions and breaks supports the broader idea that systems should consider *when* to surface attention demands.

**Codec implication:** prefer an attention inbox and mode-compatible resurfacing over interrupting for every agent or compute event.

Source:
- https://dl.acm.org/doi/fullHtml/10.1145/3313831.3376817

### 2.9 Work and non-work boundaries are behaviorally porous

Research on task management across work–life boundaries documents cross-boundary task-management behavior and opportunities for tools that support suspended work.

**Codec implication:** use one underlying graph with user-controlled lenses rather than assuming separate personal and professional systems are cognitively accurate.

Source:
- https://dl.acm.org/doi/10.1145/3582429

## 3. Distinctive hypotheses worth testing

These are not all established research findings. They are product/research hypotheses Codec can explore.

### H1 — Frontier is a better operational abstraction than task completion
A compact current-frontier description may be more valuable for knowledge work than percent complete or long task lists.

### H2 — Attention fit can route work better than priority alone
The system may become more useful by matching work to available cognition—deep, build, supervise, glance, consume—than by producing a universal ranked list.

### H3 — Prepared work packets convert scarce deep cognition into future low-attention productivity
A high-focus session can create `READY_TO_DELEGATE` inventory that later advances during gaming, fragmented time, or other low-decision periods.

### H4 — Human–machine latency hiding is a real personal productivity primitive
Parallel compute/agent work can be scheduled so machine latency occurs while the human is occupied elsewhere, with human attention requested only at useful checkpoints.

### H5 — Adoption is the missing state in many AI workflows
Separating `RESULT_READY` from `ACCEPTED` may reduce epistemic slippage in agentic development.

### H6 — Semantic provenance is more useful than exhaustive activity logging
Recording “source spawned question → report transformed into audio → listening spawned thread” may preserve intellectual lineage without the noise/privacy cost of lifelogging.

### H7 — Personal work graphs can compile minimal agent context
A rich long-term graph may support smaller, more relevant context envelopes than dumping entire chat/project histories into every agent interaction.

## 4. Roadmap

### Horizon 0 — Weekend V0: Cockpit

**Goal:** prove that Codec reduces friction today.

Capabilities:

- living threads;
- Now + Mission Control;
- frontier;
- Park / Resume;
- attention queues/modes;
- voice-friendly updates;
- surface links;
- basic event history;
- waiting/resume conditions.

Key question:

> Do I actually reach for Codec while doing real work?

### Horizon 1 — Re-entry and structured capture

Add only after V0 evidence:

- better automatic extraction from dictated updates;
- episode summaries;
- uncertainty / unresolved-decision capture;
- stale-frontier detection;
- better briefing compiler;
- friction log review;
- minimal relations/provenance.

Key question:

> Can Codec reliably preserve cognitive state without demanding maintenance?

### Horizon 2 — Dispatch and adoption

Introduce explicit work packets and machine runs.

Capabilities:

- Prepare for Later;
- desired outcome;
- constraints;
- stop conditions;
- authority level;
- expected evidence;
- review requirement;
- result/adoption lifecycle.

Key question:

> Can deep planning be safely converted into later low-attention execution?

### Horizon 3 — Antigravity integration

Current Antigravity product surfaces make this plausible as of 2026-08-15: MCP, plugins, and a Python SDK all exist in official documentation.

First integration:

- Codec exposes an MCP server.
- Antigravity can read current thread context.
- Antigravity reports meaningful transitions, blockers, results, and review requests.

Later:

- Codec dispatches a work packet through the Antigravity SDK.
- run status appears in Running;
- meaningful artifacts attach to the thread;
- completion routes to Needs You rather than silently closing the work.

Sources:
- https://antigravity.google/docs/mcp
- https://antigravity.google/docs/plugins
- https://antigravity.google/docs/sdk/overview

### Horizon 4 — Context router

Codec becomes a provider-neutral context compiler.

For any thread + objective + surface, compile:

- intent/goal;
- frontier;
- relevant decisions;
- last accepted evidence;
- constraints;
- current branch/files;
- known blockers;
- minimal related history.

Targets can include:

- Antigravity;
- ChatGPT;
- local models;
- Codex-like agents;
- other future systems.

Principle:

**Store richly. Compile sparingly.**

Key question:

> Can Codec eliminate repeated context reconstruction without flooding agents with irrelevant history?

### Horizon 5 — Attention-aware execution

Use explicit user mode plus observed behavior.

Capabilities:

- human-attention estimates;
- filter/rank by attention fit;
- identify work suitable for gaming/supervision periods;
- identify audio/research suitable for consumption;
- show deep-work inventory separately from glance work;
- learn from actual accept/reject/complete behavior.

Avoid turning this into behavioral paternalism. User intent remains primary.

Key question:

> Does matching work to cognition actually improve throughput and subjective ease?

### Horizon 6 — Conditional reactivation

Resume conditions begin to observe the world.

Potential signals:

- agent run completes;
- filesystem artifact appears;
- GitHub check finishes;
- email/reply arrives;
- dataset becomes available;
- scheduled time arrives;
- external API state changes.

Codec moves a thread from Waiting to Needs You/Ready only when its condition is satisfied.

Key question:

> Can the system hold prospective memory without creating a notification firehose?

### Horizon 7 — Provenance / epistemic graph

Codec becomes able to answer:

- Where did this idea come from?
- Which evidence supports this decision?
- Which agent produced this claim?
- Was that result ever reviewed?
- Which later work contradicted or superseded it?
- What research artifacts transformed into this current understanding?

This can bridge Codec with the broader Big Brain / long-memory architecture.

### Horizon 8 — Personal operating system for work

Long-term possibility, not commitment.

Codec may become the layer that understands:

- all living goals/threads;
- current human attention;
- delegated authority;
- active machine processes;
- external dependencies;
- available context;
- provenance;
- next human decision points.

The system could prepare future work during human-unavailable periods without taking consequential action outside explicit authority.

This is less “AI chooses what you should do” and more **an operating system scheduler for a human–machine cognitive environment**.

## 5. Possible innovations to prototype later

### 5.1 Attention budget
Instead of time estimates alone, describe required human involvement:

```text
setup: 8 min DEEP
machine: 35 min PASSIVE
checkpoint: 2 min GLANCE
machine: 20 min PASSIVE
review: 6 min SUPERVISE
```

This more accurately represents AI-era work than a single “1 hour” estimate.

### 5.2 Prepared inventory
A queue of work packets already thought through enough to execute under lower attention.

Useful before gaming or fragmented periods.

### 5.3 Context debt
Threads accumulate “context debt” when frontier/next-action information becomes stale or contradictory.

Codec can flag that re-entry will be expensive before the user discovers it manually.

### 5.4 Epistemic adoption ledger
For AI-produced decisions, fixes, or claims:

```text
PROPOSED → TESTED → REVIEWED → ACCEPTED → SUPERSEDED
```

This could become especially valuable in software development and research.

### 5.5 Mission briefing generation
Before entering a thread, Codec generates a 30-second spoken briefing suitable for headphones.

### 5.6 Session handoff audio
When parking, dictated notes can later be replayed or synthesized as a brief personalized re-entry summary.

### 5.7 Attention inbox batching
Instead of notifying on each machine event, Codec batches small review items into a supervision pass.

### 5.8 Cross-thread collision detection
If multiple threads depend on the same schema, artifact, external person, or decision, Codec surfaces the relationship before duplicate work diverges.

### 5.9 What changed while I was away?
For long-lived threads, generate a delta briefing from the last active episode rather than a full historical summary.

### 5.10 Thread spawning from provenance
A consumed research artifact or reflection can spawn a new thread while maintaining its lineage automatically.

## 6. Risks

### Risk: Codec becomes administrative overhead
Mitigation: voice-first transitions; minimal required fields; aggressively delete unused metadata.

### Risk: automatic interpretation creates correction work
Mitigation: visible compact confirmation; keep deterministic manual quick actions; measure correction frequency.

### Risk: too much AI activity produces more review burden
Mitigation: explicit work packets, stop conditions, review requirements, and adoption states.

### Risk: the cockpit becomes visually noisy
Mitigation: Now vs Mission Control, attention queues, progressive disclosure, user-controlled filters.

### Risk: personal/professional integration feels invasive
Mitigation: domains/lenses, local-first storage, explicit visibility controls, no moralized ranking.

### Risk: over-integration creates brittleness
Mitigation: shallow URL/surface links first; add adapters only after repeated manual behavior proves their value.

### Risk: historical/provenance capture becomes lifelogging
Mitigation: capture semantic transitions and lineage, not raw clickstreams.

### Risk: system starts optimizing the user instead of serving the user
Mitigation: explicit modes, override everywhere, suggestions rather than mandates, no universal productivity score.

## 7. Research agenda Codec itself could generate

If the project grows, its own usage can become a source of empirical questions:

- How long does re-entry take with and without a structured briefing?
- Which frontier fields predict successful resumption?
- Which attention modes are stable versus context-specific?
- Can human attention requirements be predicted from prior episodes?
- Does preparing work packets before low-attention periods increase useful parallelism?
- How often are agent-produced outputs accepted, rejected, or revised?
- Which kinds of context improve agent performance versus create noise?
- What semantic provenance do users actually revisit months later?
- How frequently does cross-thread dependency detection prevent duplicated work?

This is where Codec could become not only a useful personal tool but a real experiment in human–agent activity-centric computing.

## 8. Current product/integration landscape — 2026-08-15

### Google Antigravity
Official docs currently describe Antigravity 2.0 as a desktop application for managing AI agents and document support for MCP, plugins, and a Python SDK. That makes Antigravity a promising execution layer under Codec rather than something Codec should reproduce.

- https://antigravity.google/docs/overview
- https://antigravity.google/docs/mcp
- https://antigravity.google/docs/plugins
- https://antigravity.google/docs/sdk/overview

### ChatGPT
Projects currently provide grouped chats/files/instructions and ongoing project context. For Codec V0, a ChatGPT conversation/project is best treated as a linked Surface rather than assuming deep automatic ingestion. API-managed Conversations are a separate developer surface and can be explored for Codec-created workflows later.

- https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- https://openai.com/academy/projects/
- https://platform.openai.com/docs/api-reference

## 9. A Metal Gear-inspired north-star framing

The original Codec metaphor is useful because it is **mission support**, not the mission itself.

Codec-the-app should not become another place where work has to be performed for the sake of the tool. Its job is to keep the mission legible while activity jumps across tools, actors, and attention states.

If it works, the feeling should be:

> I can leave this. The state is safe. I know what is running. I know what needs me. I can come back.

That is the product.
