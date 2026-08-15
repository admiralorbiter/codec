# Codec — UX / UI Specification

> “Kept you waiting, huh?”


## 1. UX objective

Codec should feel like a **personal command surface**, not a database editor.

The application can be visually dense. It must be interaction-light.

### Primary interaction rule

**Glance → click → dictate → done.**

Typing should be unnecessary for normal operation.

### Primary navigation rule

**The graph is underneath the interface, not the interface itself.**

The daily UX is organized around attention and current work state. A graph explorer can exist later for history, provenance, and discovery.

## 2. Core views

Codec needs two top-level operational lenses from V0.

### 2.1 Focus / Now
Shows only threads plausibly relevant to the current session.

Use when actively working, supervising agents, gaming while monitoring work, consuming research, etc.

### 2.2 Mission Control / All Living
Shows all living threads across domains with high information density.

Use for orientation, weekly review, choosing what to activate, or checking whether anything has been forgotten.

The user should switch between these views with one control. They are not separate data models.

## 3. Attention mode

Persistent top-level selector:

`DEEP` · `BUILD` · `SUPERVISE` · `CONSUME` · `OPEN`

Optional later modes: `GLANCE`, `OFFLINE`, `PIANO`, or custom contexts. V0 should avoid overfitting named life activities; modes should describe attention capability.

### Effect

The mode changes ranking and visibility, not truth.

Example:

- **DEEP:** surfaces unresolved reasoning and decision-heavy work; suppresses low-value interruptions.
- **BUILD:** emphasizes interactive development and testing.
- **SUPERVISE:** emphasizes running agents, results needing quick review, compute checkpoints, and prepared dispatches.
- **CONSUME:** emphasizes audio, reading, video, and research outputs that are ready.
- **OPEN:** minimal filtering; user chooses.

A toggle should allow **Show all anyway**.

## 4. Cockpit layout — desktop

Suggested high-level composition:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ CODEC        [Now | Mission Control]        Mode: SUPERVISE     🎙 Capture │
├──────────────────────┬──────────────────────────────────────┬───────────────┤
│ Filters / domains    │ ATTENTION QUEUES                     │ Thread drawer │
│                      │                                      │               │
│ All                  │ NEEDS YOU                            │ Frontier      │
│ Professional         │ ┌──────────────────────────────────┐ │ Resume capsule│
│ Research             │ │ Recurrence / baseline           │ │ Next action   │
│ Creative             │ │ Needs decision · 2–5 min        │ │ Surfaces      │
│ Personal             │ └──────────────────────────────────┘ │ Recent events │
│                      │                                      │ Relations     │
│ Projects             │ RUNNING                              │               │
│ Polaris              │ ┌──────────────────────────────────┐ │ [Resume]      │
│ LAT                  │ │ LAT refactor · Antigravity      │ │ [Park]        │
│ Recurrence           │ │ Step 3/5 · tests passing        │ │ [Dispatch]    │
│                      │ └──────────────────────────────────┘ │ [Update 🎙]    │
│                      │                                      │               │
│                      │ READY                                │               │
│                      │ WAITING                              │               │
└──────────────────────┴──────────────────────────────────────┴───────────────┘
```

The right drawer should open without leaving the cockpit. Thread switching should feel immediate.

## 5. Attention queues

The default Now view should group cards by **what relationship the thread currently has to human attention**.

### Needs You
Human cognition is currently the bottleneck.

Examples:
- decision required;
- review required;
- unresolved reasoning;
- agent blocked on a question.

### Running
Machine or external work is actively progressing.

Examples:
- Antigravity agent executing;
- local computation;
- report/audio/video generation;
- long-running script.

### Ready
Work is executable and prepared but not currently running.

Examples:
- work packet ready for Antigravity;
- computation ready to launch;
- source ready for deep research;
- test plan ready to execute.

### Waiting
The next action depends on an external condition.

Every waiting item should show the condition, not merely a status label.

Example:

> **Waiting on:** Pathful export  
> **Then:** validate import and inspect unmatched teachers

### Consumable
This can either be its own queue or be emphasized only in CONSUME mode.

Examples:
- Notebook/LLM-generated podcast ready;
- report ready to read;
- video ready to watch.

### Parked
Not shown in Now by default. Visible in Mission Control.

## 6. Thread card anatomy

Cards should be compact but information-rich.

Required V0 content:

1. **Thread name**
2. **Parent/project** (small)
3. **Attention/state badge**
4. **Actor/surface**
5. **Frontier** — 1–2 lines
6. **Next interaction** — one line
7. **Last meaningful change** — relative time

Example:

```text
LAT · Capture pipeline
RUNNING · ANTIGRAVITY
Refactoring ingestion around new event model.
Next: quick review when test suite completes.
Last change: tests 18/24 passed · 7m ago
```

Optional metadata should appear only when relevant:

- expected compute duration;
- human attention estimate;
- resume condition;
- uncertainty marker;
- adoption/review requirement;
- related thread count;
- artifact count.

## 7. Thread drawer

Opening a thread should reveal detail through progressive disclosure rather than navigation to a giant project-management screen.

### Section A — Frontier
Large, readable current-state statement.

### Section B — Next
- next action;
- attention fit;
- actor;
- resume condition if waiting.

### Section C — Briefing / Resume capsule
Compact reconstruction of where the user left off:

- What was being attempted?
- What changed?
- What is uncertain?
- Why did work stop?
- What should happen first on re-entry?

### Section D — Surfaces
One-click links:

- Antigravity conversation/workspace;
- ChatGPT conversation/project;
- GitHub branch/PR;
- local directory;
- source page;
- report/audio/video;
- any other relevant URI/path.

### Section E — Recent episodes/events
Chronological, concise. No firehose.

### Section F — Relations
Small list in V0. Graph visualization later.

## 8. Universal voice capture

A persistent microphone control is central to the product.

### Invocation
One click/tap.

### User says

> Finished the first recurrence run. The persistence effect looks interesting, but I need the shuffled baseline before I believe it. I started that run now; it should take about 35 minutes.

### Codec should propose

- append RESULT / OBSERVATION event;
- update frontier;
- create/mark computation RUNNING;
- next action = compare with shuffled baseline;
- attention state = PASSIVE until result;
- expected check = ~35 min.

### Confirmation UX
Do not show a form with eight fields.

Show a compact proposed interpretation:

```text
Update Recurrence / persistence
✓ Result observed
✓ Baseline compute running (~35m)
✓ Next: compare outputs

[Save] [Edit interpretation] [Cancel]
```

One-tap save should be the normal path.

### V0 voice implementation
Prefer a pragmatic implementation that can be dogfooded immediately:

1. Browser speech-recognition API where supported, **or** OS dictation into the capture surface.
2. Keep the capture UI compatible with a future server-side/local transcription pipeline.
3. Do not couple the data model to any specific speech provider.

## 9. Quick-transition controls

The most common state changes should take one click.

Suggested thread actions:

- **Resume**
- **Park**
- **Update 🎙**
- **Launch / Dispatch**
- **Wait**
- **Needs Review**
- **Accept**
- **Rework**
- **Done / Close**

Avoid a generic status dropdown with 20 options.

The action menu should be contextual: a running thread needs `Result` or `Stop`, not `Launch`.

## 10. Park flow

Parking is not “set status = paused.”

Tap **Park** → microphone opens automatically.

Prompt:

> **Where are you leaving this?**

Optional follow-up only if needed:

> **What makes it actionable again?**

Codec extracts the resume capsule and shows one confirmation card.

Target interaction time: tens of seconds, primarily voice.

## 11. Resume flow

Tap **Resume**.

The drawer should immediately show:

```text
LAST ACTIVE: Yesterday, 4:42 PM

WHERE YOU LEFT IT
The import works on sample data. Real-data validation remains.

WHY IT STOPPED
Waiting for Pathful teacher/section export.

WHAT CHANGED
Export attached this morning.

FIRST MOVE
Run import against new snapshot; inspect unmatched teachers.

SURFACES
[Antigravity] [Branch] [Dataset] [Prior ChatGPT analysis]
```

Then one primary CTA:

**Begin episode**

Later, this may also compile and dispatch context into the chosen AI surface.

## 12. Delegated / agent UI

The agent interface should hide low-level logs until requested.

Default card should expose:

- objective;
- current phase;
- last meaningful event;
- whether human action is required;
- review/adoption status.

Example:

```text
LAT ingestion refactor
ANTIGRAVITY · RUNNING
Phase 3/5: migrate capture handlers
Last event: unit tests passed
Human action: none
```

When attention is needed:

```text
LAT ingestion refactor
NEEDS YOU · DECISION
Agent found two storage approaches.
Estimated attention: 2–5 min
[Review]
```

The estimate can be manually/AI-generated and should be treated as advisory.

## 13. Attention inbox

Notifications should generally land in an inbox-like queue instead of interrupting the current task.

Examples:

- agent result ready;
- compute completed;
- external dependency arrived;
- review requested;
- waiting condition satisfied.

Codec may visually emphasize these when entering a compatible mode or after a thread transition.

V0 should **not** implement aggressive push notifications.

## 14. Mission Control / All Living

This is the high-density view the user explicitly wants.

Possible structure:

- sortable table or dense card matrix;
- grouped by project/domain, attention state, or actor;
- persistent filter chips;
- quick search;
- status/attention counts;
- “stale frontier” indicator for threads not updated recently;
- one-click activation into Now.

Recommended default columns if table-like:

| Thread | Project | Frontier | State | Actor | Attention | Next | Updated |
|---|---|---|---|---|---|---|---|

No requirement for percent complete.

## 15. Mobile / secondary-device behavior

Mobile is primarily for:

- voice capture;
- quick review;
- accepting/reworking agent outputs;
- checking Running / Needs You;
- switching attention mode;
- listening/consuming links.

It should not attempt to reproduce every dense desktop panel at once.

Recommended mobile bottom navigation:

`Now` · `Living` · `Capture` · `Search`

Thread detail opens full-screen.

## 16. Progressive structure

### New thread flow

Tap **+ Thread**.

Required:
- name (voice allowed).

Optional:
- project/domain;
- dictate intent.

Then create.

No required:
- due date;
- priority;
- tags;
- owner;
- workflow;
- estimate;
- dependencies;
- agent settings.

All of those appear only when the thread develops a need for them.

## 17. Visual language

Codec can embrace a restrained tactical / terminal influence without becoming a cosplay HUD.

Recommended character:

- dark-friendly but not dark-only;
- strong hierarchy;
- compact typography;
- narrow colored state accents, not rainbow cards;
- monospace only for IDs, paths, commands, and machine state;
- human prose remains highly readable;
- subtle “radio / mission-control” language in labels where it helps.

Potential easter eggs belong in microcopy, not core functionality.

## 18. UX anti-patterns

Do not build:

- drag-and-drop as the only way to update state;
- a Kanban board as the universal representation;
- dozens of mandatory fields;
- a giant always-visible graph;
- a live agent log as the default agent UI;
- AI-assigned universal priority scores;
- automatic life-scheduling that overrides stated intent;
- modal dialogs for common state changes;
- notifications for every machine event;
- separate professional/personal databases.

## 19. V0 usability targets

Dogfood metrics can be qualitative initially, but the following targets are useful:

- Create new thread: **< 15 sec** with voice.
- Park thread with useful re-entry state: **< 45 sec**.
- Resume and understand frontier: **< 15 sec**.
- Mark a common transition: **1 click + optional voice**.
- Find associated surface: **≤ 2 clicks**.
- No normal workflow should require editing a database-like form.

## 20. Research-backed UI rationale

- Interruption/resumption work supports explicit re-entry cues and context reconstruction.
- Activity-centric computing supports organizing resources around ongoing activities rather than applications.
- Google PAIR recommends progressive disclosure and feedback/control loops rather than exposing unnecessary AI complexity.
- Research on opportune transitions suggests timing matters when presenting interruptions or task-switch suggestions.
- Human–AI research emphasizes preserving user control and reducing metacognitive/setup burden.

### Sources

- https://www.microsoft.com/en-us/research/publication/evaluating-cues-for-resuming-interrupted-programming-tasks/
- https://dl.acm.org/doi/10.1145/1040830.1040855
- https://dl.acm.org/doi/fullHtml/10.1145/3313831.3376817
- https://pair.withgoogle.com/guidebook/chapters/trust-and-explanations/crafting-helpful-explanations
- https://pair.withgoogle.com/guidebook/chapters/feedback-and-controls/design-ai-feedback-loops
- https://research.ucc.ie/en/publications/generative-ai-at-work-mundane-and-productive-articulation/
