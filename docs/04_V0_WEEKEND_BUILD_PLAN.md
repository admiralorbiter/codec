# Codec — V0 Weekend Build Plan

## 1. Mission

Build the smallest Codec that can be used on real work **immediately**.

The V0 is successful if it becomes the preferred surface for:

- seeing living threads;
- deciding what can be worked on now;
- parking a thread;
- resuming a thread;
- tracking basic human/agent/compute/waiting state;
- opening the relevant work surfaces.

This is a dogfood experiment, not a platform launch.

## 2. The Shadow Moses test

The system must survive one messy real weekend containing a mix of:

- LAT development;
- multiple recurrence research threads;
- learning/research transformed into audio/video;
- some professional development;
- agent runs;
- local compute;
- gaming/supervision/consumption periods;
- piano / intentionally unavailable attention;
- movie/reflection time;
- thread switching and return after hours or days.

If Codec requires constant cleanup to represent this weekend, the ontology or UX is wrong.

## 3. V0 scope

### Must have

- Project CRUD, minimal.
- Thread creation with almost no required metadata.
- Now view.
- Mission Control / All Living view.
- Attention-mode selector.
- Thread cards.
- Thread detail drawer/page.
- Update event.
- Park flow.
- Resume flow.
- State transitions: Needs You, Ready, Running, Waiting, Parked, Done.
- Frontier.
- Next action.
- Resume condition.
- Surfaces / links.
- Recent event history.
- Voice/dictation-friendly capture surface.
- Responsive enough for phone use.

### Should have if cheap

- Actor selection: Me / Antigravity / ChatGPT / Compute / External.
- Attention fit.
- expected compute duration.
- “needs quick review” marker.
- lightweight thread relations.
- one-click open of stored URLs.
- basic search/filter.

### Explicitly defer

- automatic ChatGPT ingestion;
- automatic Antigravity status synchronization;
- MCP server;
- Antigravity SDK dispatch;
- embeddings/vector search;
- graph visualization;
- predictive attention modeling;
- automated trigger monitoring;
- reminders/notifications;
- multi-user support;
- elaborate analytics.

## 4. Build order

### Phase 0 — skeleton and sample data

Build:

- Flask app;
- SQLite schema;
- base template;
- fixtures representing actual current threads.

Seed with realistic examples rather than lorem ipsum:

- LAT development;
- recurrence research A;
- recurrence research B;
- mechanics learning / source → research → media;
- at least one professional project thread;
- one running process;
- one waiting dependency.

**Exit criterion:** `/` renders a static cockpit using real-looking data.

### Phase 1 — cockpit before backend sophistication

Implement the UX first:

- Now / Mission Control toggle;
- attention-mode selector;
- Needs You / Running / Ready / Waiting sections;
- dense thread cards;
- drawer.

Do not start with forms or admin screens.

**Exit criterion:** looking at the cockpit already feels useful even if updates are still manual.

### Phase 2 — core thread transitions

Implement domain commands:

- create thread;
- update;
- park;
- resume;
- wait;
- mark running;
- result ready;
- accept;
- close.

Each command:

1. validates transition;
2. updates current thread projection;
3. appends an event.

**Exit criterion:** normal usage does not require directly editing fields.

### Phase 3 — Park / Resume

This is the highest-value workflow.

Park UX:

- click Park;
- dictate/type free-form state;
- capture frontier, stopping reason, next action, resume condition;
- confirm;
- save.

If AI parsing would slow initial implementation, use a **single natural-language park note plus optional quick chips** first. The data model should support later extraction.

Resume UX:

- display briefing automatically;
- show surfaces;
- one-click Begin Episode.

**Exit criterion:** a thread can be abandoned for an hour and resumed without checking old chat windows first.

### Phase 4 — voice

Implement the fastest practical voice path.

Option A:
- browser speech recognition;
- transcript enters universal capture.

Option B:
- OS dictation in the focused capture field;
- add one-click focus and auto-submit ergonomics.

Optional later:
- MediaRecorder → local/server transcription.

Voice should work for:

- new thread;
- update;
- park;
- add surface note;
- quick result/review note.

**Exit criterion:** common updates can be performed without physical typing.

### Phase 5 — surfaces

Add a very lightweight surface manager.

Fields:

- label;
- type;
- URI or path.

Fast presets:

`ChatGPT` · `Antigravity` · `GitHub` · `Local` · `Web` · `Audio` · `Other`

**Exit criterion:** finding the right ChatGPT/Antigravity/repo/source is faster through Codec than through window hunting.

### Phase 6 — dogfood instrumentation

Do not add traditional product analytics. Add a tiny **friction log**.

A persistent action:

**This was annoying**

Voice note accepted.

Capture:

- current page/thread;
- timestamp;
- user complaint.

Also allow:

**I needed something Codec didn't have**

This produces the V1 requirements from actual use.

## 5. Suggested V0 screens/routes

```text
GET  /                       cockpit / Now
GET  /living                 Mission Control
GET  /threads/<id>           thread detail if drawer fallback needed
POST /threads                create
POST /threads/<id>/update
POST /threads/<id>/park
POST /threads/<id>/resume
POST /threads/<id>/transition
POST /threads/<id>/surfaces
POST /capture                universal capture
GET  /search
```

HTMX partials can make most actions feel immediate.

## 6. Minimum schema for weekend build

If time/complexity pressure appears, reduce to:

```text
Project
Thread
Event
Surface
```

Episode can be added once Park/Resume is stable. Relation can be added once a real cross-thread relationship needs representation.

The conceptual architecture remains richer than the first migration.

## 7. V0 state model

```text
             ┌───────────────┐
             │   NEEDS_YOU   │
             └───────┬───────┘
                     │ prepare/delegate
                     v
┌────────┐       ┌────────┐       ┌──────────┐
│ PARKED │ <-->  │ READY  │ ----> │ RUNNING  │
└────────┘       └────────┘       └────┬─────┘
                                      │ result
                                      v
                                 ┌───────────┐
                                 │NEEDS_YOU  │
                                 │  REVIEW   │
                                 └─────┬─────┘
                                       │ accept
                                       v
                                    ACTIVE

WAITING is entered whenever advancement depends on an external condition.
DONE removes the thread from living views.
```

Keep transition semantics flexible during dogfooding.

## 8. Suggested quick actions by state

### ACTIVE / NEEDS YOU
`Update` · `Park` · `Wait` · `Prepare` · `Done`

### READY
`Launch` · `Update` · `Park`

### RUNNING
`Update` · `Result Ready` · `Blocked` · `Stop`

### WAITING
`Condition Met` · `Update` · `Park`

### REVIEW
`Accept` · `Rework` · `Update`

## 9. Dogfood protocol

For the first weekend, do not try to migrate every historical project.

Only enter **currently living threads**.

Whenever real behavior disagrees with the model:

1. do the real work first;
2. record the friction;
3. change Codec after observing repetition.

Do not contort behavior to satisfy the app.

### Questions to observe

- Do threads feel like the correct granularity?
- When do you naturally create a new thread versus an episode?
- Which card information do you repeatedly look for?
- Which fields go stale?
- Does Park capture enough for Resume?
- Is attention mode useful or decorative?
- Are Needs You / Running / Ready / Waiting the right queues?
- Which voice updates are easy to interpret automatically?
- When does a project hierarchy help?
- What real relationships appear between threads?
- Do agent results need richer adoption/review states?
- What causes you to abandon Codec and hunt through windows manually?

## 10. Success / failure evidence

### Strong positive evidence

- Codec becomes the first place checked when changing work.
- You resume without reopening several old chats to remember context.
- Running/waiting processes no longer occupy working memory.
- You use voice updates willingly because they feel cheaper than remembering.
- Mission Control provides confidence that no living thread has disappeared.
- During SUPERVISE periods, Codec becomes a useful queue of small interventions.

### Negative evidence

- you skip updates because they feel like bookkeeping;
- frontier summaries are routinely stale or wrong;
- thread creation requires too much categorization;
- the attention queues do not match actual behavior;
- the app becomes another window you have to manage;
- you still rely on notebook memory because Codec's capture is slower;
- automatic parsing creates enough corrections to become annoying.

Negative evidence should trigger simplification before adding features.

## 11. After the weekend

The first review should produce:

1. **Keep** — interactions that already reduce friction.
2. **Kill** — fields/actions that created administration.
3. **Fix** — recurring friction in core flows.
4. **Add** — missing concepts proven by real work.
5. **Automate** — transitions repeatedly performed manually and therefore worth integration.

Only the fifth category should drive MCP/API integration work.

## 12. First integration candidate

If dogfooding shows that Antigravity status updates are frequent and useful, the first serious integration should likely be a **tiny Codec MCP surface**, not a full bidirectional orchestration system.

Initial tools:

```text
get_thread_context(thread_id)
record_update(thread_id, text)
record_blocker(thread_id, text)
record_result(thread_id, text, surface?)
request_review(thread_id, summary)
```

That is enough to test whether work can update the control plane without creating new supervision overhead.

## 13. The V0 rule

When deciding whether to add something this weekend, ask:

> Will I plausibly use this in the next 24 hours?

If no, document it in the roadmap and keep building the cockpit.
