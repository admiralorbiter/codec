# Codec — Vision & Product Principles

## 1. Vision

Modern work is no longer a sequence of tasks completed by one person inside one application.

A single line of work may move through:

- focused human reasoning;
- ChatGPT research or synthesis;
- Antigravity development;
- a local Python computation;
- an audio generation pipeline;
- passive waiting on an external dependency;
- a quick human review;
- another agent;
- a notebook reflection;
- and back into focused human reasoning days later.

Conventional project-management software usually models the **administration of work**: items, owners, statuses, due dates, priorities, and boards. Codec instead models the **continuity of work**.

The core questions are:

- What lines of work are alive?
- Where is each one now?
- Who or what has the ball?
- What can continue without human cognition?
- What needs a glance, supervision, consumption, or deep thought?
- Why did this thread stop?
- What condition makes it actionable again?
- What changed while attention was elsewhere?
- What is the minimum sufficient context needed to resume?
- How did this result or idea come to exist?

## 2. Core mental model

### Project
A durable neighborhood of work. Useful for grouping, but not the primary operational unit.

Examples: Polaris, LAT, Roll Call, Big Brain Time.

### Thread
A durable line of work, inquiry, problem, or responsibility.

A thread can live for hours, months, or years. It can move among tools and actors without becoming a new thread.

### Frontier
The most important concept in Codec.

The frontier is a compact statement of **where the thread actually is now**. It should be human-readable and immediately useful for re-entry.

Bad frontier:

> Teacher dashboard — 70% complete.

Good frontier:

> Dashboard implementation works on sample data. Real-data validation is blocked on the Pathful export; unmatched-teacher behavior is still uncertain.

### Episode
A bounded period of activity on a thread.

Episodes terminate. Threads may not.

### Event
A meaningful transition or observation within a thread: started, discovered, delegated, blocked, waiting, result ready, accepted, parked, resumed, etc.

### Surface
Where work lives or occurs: Antigravity, ChatGPT, GitHub, local folder, browser page, notebook, audio file, email, meeting, terminal.

### Actor
Who or what currently advances the work: human, Antigravity agent, ChatGPT, local process, external person, scheduled job.

### Artifact / Evidence
Something produced or used: commit, report, audio, dataset, test output, decision, transcript, screenshot, note.

### Relation
A semantic edge between objects: depends_on, blocked_by, spawned_from, informed_by, supersedes, tests, transforms_into, shares_artifact.

### Resume condition
A cue that turns a waiting thread into an actionable one.

> When the Pathful export arrives → run validation and inspect unmatched teachers.

### Attention fit
The kind of cognition required to advance the work.

Initial vocabulary:

- **DEEP** — sustained reasoning / decision making
- **BUILD** — interactive implementation
- **SUPERVISE** — intermittent checks of delegated work
- **GLANCE** — quick approval, classification, or inspection
- **CONSUME** — listen/read/watch
- **PASSIVE** — compute or external waiting; no human attention

These are not personality labels. They describe the **shape of an interaction**.

## 3. Product principles

### 3.1 Capture transitions, not administration
Codec should ask for input when something meaningful changes, not because a database field wants maintenance.

Useful transitions:

- I started.
- I discovered something.
- I delegated this.
- I launched computation.
- I need a decision.
- I am blocked.
- I am waiting.
- A result arrived.
- I accepted/rejected the result.
- I am leaving this thread.
- I resumed.

If a field can be inferred from those events, infer it.

### 3.2 Glance first, click second, dictate third, type almost never
Typing is high-friction for the intended workflow. Voice capture is a first-class product requirement, not a later accessibility feature.

Buttons handle common transitions. Dictation handles nuance. Typing exists as an escape hatch.

### 3.3 Dense information is acceptable; administrative interaction is not
Codec can look information-rich. The user explicitly prefers detail and can tolerate visual density. The danger is not seeing a lot; the danger is being forced to maintain a lot.

### 3.4 General at creation, specific through use
New threads must take seconds to create.

A new thread starts with almost nothing:

- name;
- optional parent/project;
- optional dictated intent.

It gains structure only when real work demands it. A thread that never uses agents should never require agent configuration. A thread with no dependency should never ask for a resume condition.

**Never make the user model the future before experiencing it.**

### 3.5 Park / Resume is a primary interaction
Interruption research consistently shows that reconstructing conceptual context is a real cost. Codec therefore treats leaving and re-entering work as first-class workflows rather than incidental navigation.

Parking should preserve:

- frontier;
- unresolved uncertainty;
- why work stopped;
- next action;
- resume condition, if any;
- relevant surfaces.

Resuming should reconstruct these in seconds.

### 3.6 One work graph, multiple lenses
Professional, research, creative, learning, personal, and recreational life belong to one underlying graph because the scarce resource is shared human attention.

The UI can provide strong filters and lenses without creating disconnected systems.

### 3.7 Preserve productive articulation; eliminate mundane articulation
It is useful to make the user clarify:

> What am I actually trying to accomplish?

It is not useful to make the user repeatedly explain:

> What is Polaris? Which branch? What did the prior agent do? What constraints already exist?

Codec should preserve the first kind of thinking and automate the second.

### 3.8 Store richly, compile sparingly
The system can retain extensive history and provenance. Individual human or agent interactions should receive only the context relevant to the current objective.

The graph is a memory substrate. The context packet is a compiled view.

### 3.9 Agent completion is not work completion
Delegated work passes through an adoption boundary.

Typical lifecycle:

`READY_TO_DELEGATE → RUNNING → RESULT_READY → NEEDS_REVIEW → ACCEPTED`

or

`... → NEEDS_REVIEW → REWORK / REJECTED`

This prevents “agent produced output” from being confused with “we know this is correct.”

### 3.10 Waiting is work state, not absence of work
Waiting should record the dependency and the reactivation cue.

A parked thread can be intentionally dormant. A waiting thread has a known condition that can make it actionable.

### 3.11 No notification firehose
Events should generally accumulate into an **attention inbox** rather than interrupt the current thread. Codec should surface them at sensible transition points or when the user enters a compatible attention mode.

### 3.12 The application should not moralize
Codec should not tell the user that professional work is inherently more virtuous than research, music, gaming, film, or personal projects.

It should answer:

> Given what I want right now and the attention I have, what can productively happen?

## 4. What Codec is becoming

A useful hierarchy for future thinking:

1. **Thread cockpit** — know the current frontier of living work.
2. **Re-entry system** — reconstruct suspended cognition quickly.
3. **Context router** — compile the right context for a human or AI surface.
4. **Human–agent control plane** — track delegated work, computation, checkpoints, and adoption.
5. **Attention-aware scheduler** — match executable work to available cognition.
6. **Provenance system** — preserve the lineage of decisions, research, transformations, and artifacts.
7. **Anticipatory work substrate** — prepare likely next work during machine-idle or human-unavailable periods, within explicit authority boundaries.

The V0 should serve level 1 and level 2 extremely well while leaving clean seams for the rest.

## 5. Design test

Every proposed feature should answer at least one of these:

- Does this reduce re-entry cost?
- Does this reduce mundane coordination with AI/tools?
- Does this expose a meaningful work transition?
- Does this help allocate attention?
- Does this preserve evidence/provenance?
- Does this make delegation safer or easier to verify?

If not, it probably does not belong in Codec yet.

---

## Research anchors

- Parnin & Rugaber, *Evaluating Cues for Resuming Interrupted Programming Tasks* — https://www.microsoft.com/en-us/research/publication/evaluating-cues-for-resuming-interrupted-programming-tasks/
- Iqbal & Horvitz, *Disruption and Recovery of Computing Tasks* — https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/CHI_2007_Iqbal_Horvitz-1.pdf
- TaskTracer — https://dl.acm.org/doi/10.1145/1040830.1040855
- Gollwitzer, *Psychology of Planning* (2025) — https://www.annualreviews.org/content/journals/10.1146/annurev-psych-021524-110536
- Tankelevitch & Rintel, *Goals as First-Class Abstractions in Human-AI Collaboration* (2026) — https://www.microsoft.com/en-us/research/publication/goals-as-first-class-abstractions-in-human-ai-collaboration/
- Larsen-Ledet, *Generative AI at work: mundane and productive articulation* (2026) — https://research.ucc.ie/en/publications/generative-ai-at-work-mundane-and-productive-articulation/
