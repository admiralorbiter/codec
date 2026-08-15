# Codec — System Architecture & Data Model

## 1. Architectural stance

V0 should be intentionally boring underneath the interesting ideas.

Recommended stack:

- **Python + Flask**
- **SQLite**
- **SQLAlchemy** or a thin sqlite3/repository layer
- **Jinja templates**
- **HTMX** for partial updates and low-complexity interaction
- small amount of vanilla JavaScript for voice capture, drawers, and local UI state
- local-first, single-user

The goal is to make the product cheap to change during dogfooding.

## 2. Architecture principles

### 2.1 Event log + current projection, not religious event sourcing
Keep meaningful events immutable enough to reconstruct history, but also keep current thread fields for simple queries and UI performance.

Do not force every derived field to be rebuilt on each page load.

### 2.2 Stable domain model, replaceable integrations
Codec should not fundamentally know that “work” means ChatGPT or Antigravity.

Integrations are represented as **surfaces** and **actors** with provider metadata.

### 2.3 Graph semantics on relational storage
SQLite is sufficient for V0.

A relation table provides graph edges without requiring Neo4j or a dedicated graph database.

Move to a graph database only if real queries demonstrate a need.

### 2.4 Structured state can come from natural language
Voice capture and AI parsing should generate *proposed* structured updates, not mutate hidden state without review.

### 2.5 Consequential action boundary
Future agent integrations can read broadly but should require explicit authority for consequential actions.

Codec must distinguish:

- preparing an action;
- recommending an action;
- executing an action;
- adopting/accepting an agent result.

## 3. Core V0 entities

### Project
Optional grouping container.

```text
id
name
description
domain
status
created_at
updated_at
```

### Thread
Primary operational entity.

```text
id
project_id nullable
parent_thread_id nullable
name
intent nullable
frontier nullable
state
attention_fit nullable
current_actor_id nullable
next_action nullable
resume_condition nullable
is_living boolean
created_at
updated_at
last_active_at nullable
```

Suggested `state` values for V0:

```text
ACTIVE
NEEDS_YOU
READY
RUNNING
WAITING
PARKED
DONE
```

Do not encode every nuance in `state`. Use events and attention fit for detail.

### Episode
A bounded work session on a thread.

```text
id
thread_id
started_at
ended_at nullable
mode nullable
summary nullable
ending_reason nullable
```

Episodes can initially be created explicitly by Resume/Start and ended by Park/Close. Later they can be inferred.

### Event
Meaningful append-only work transition.

```text
id
thread_id
episode_id nullable
event_type
occurred_at
actor_id nullable
summary
payload_json nullable
source_surface_id nullable
```

Suggested event types:

```text
THREAD_CREATED
STARTED
UPDATED
NOTE
DISCOVERY
DECISION
DELEGATED
LAUNCHED
BLOCKED
WAITING
RESUME_CONDITION_SET
RESULT_READY
REVIEW_REQUESTED
ACCEPTED
REJECTED
REWORK_REQUESTED
ARTIFACT_ADDED
SURFACE_ADDED
RELATION_ADDED
PARKED
RESUMED
CLOSED
```

### Surface
A durable pointer to where relevant work lives.

```text
id
thread_id nullable
surface_type
provider nullable
label
uri nullable
external_id nullable
local_path nullable
metadata_json nullable
created_at
last_used_at nullable
```

Suggested surface types:

```text
CHAT
IDE
REPOSITORY
BRANCH
FILE
FOLDER
WEBPAGE
NOTEBOOK
AUDIO
VIDEO
DATASET
TERMINAL
OTHER
```

### Actor
Who/what has the ball.

```text
id
actor_type
name
provider nullable
metadata_json nullable
```

Actor types:

```text
HUMAN
AGENT
PROCESS
EXTERNAL_PERSON
SERVICE
```

### Relation
Semantic graph edge.

```text
id
source_type
source_id
relation_type
target_type
target_id
note nullable
created_at
```

Initial relations:

```text
DEPENDS_ON
BLOCKED_BY
SPAWNED_FROM
INFORMED_BY
SUPERSEDES
TESTS
TRANSFORMS_INTO
SHARES_ARTIFACT_WITH
RELATED_TO
```

V0 UI can expose only a few relations even if the table supports more.

## 4. V0 optional entity: Artifact

This can be postponed if Surface is enough for the first weekend.

A dedicated Artifact entity becomes useful when Codec needs provenance independent of “where the thing lives.”

```text
id
thread_id nullable
artifact_type
name
uri/path nullable
content_hash nullable
summary nullable
created_at
metadata_json nullable
```

Potential types: commit, diff, report, dataset, image, audio, video, test_result, prompt, transcript, decision_record.

## 5. Future entities, deliberately not mandatory in V0

### Goal
A persistent desired outcome that can be served by multiple threads.

```text
Goal ← served_by → Thread
```

V0 uses `thread.intent` so the user does not have to administer a separate goal system.

### Work Packet / Dispatch
Prepared work that can be executed later with reduced human cognition.

Possible schema:

```text
id
thread_id
objective
instructions
constraints
stop_conditions
expected_evidence
required_review
authority_level
status
```

### Run
Machine execution with lifecycle and checkpoint data.

Useful for Antigravity, local compute, research jobs, media generation.

### Adoption record
Captures review and acceptance/rejection of an AI-produced result.

## 6. State transitions

Codec should implement transitions as commands that both update the current projection and append an event.

Examples:

### Park

```text
Thread.state = PARKED or WAITING
Thread.frontier = parsed frontier
Thread.next_action = parsed next action
Thread.resume_condition = parsed condition
Episode.ended_at = now
append PARKED or WAITING event
```

### Resume

```text
Thread.state = ACTIVE
Thread.last_active_at = now
create Episode
append RESUMED event
```

### Delegate

```text
Thread.state = RUNNING
Thread.current_actor = selected agent
append DELEGATED + LAUNCHED
```

### Result ready

```text
Thread.state = NEEDS_YOU
append RESULT_READY / REVIEW_REQUESTED
```

### Accept

```text
append ACCEPTED
update frontier from accepted result
set next state based on next action
```

## 7. Voice / natural-language interpretation architecture

V0 pipeline:

```text
voice → transcript → parse proposal → user confirmation → domain command → event + projection
```

The **parse proposal** should never directly commit complex state without a visible confirmation.

Proposed parse output:

```json
{
  "thread_id": 42,
  "events": [
    {"type": "DISCOVERY", "summary": "Persistence effect observed in first run"},
    {"type": "LAUNCHED", "summary": "Shuffled baseline run started"}
  ],
  "frontier": "Initial effect observed; shuffled baseline is now running before interpretation.",
  "next_action": "Compare baseline with first run.",
  "state": "RUNNING",
  "attention_fit": "PASSIVE",
  "expected_wait_minutes": 35
}
```

The parser can initially be a very small LLM call or simple manually structured UI. The interface should work even before AI parsing is perfect.

## 8. Thread briefing compiler

Even V0 can build a deterministic resume capsule from current fields and recent events.

Input:

- intent;
- frontier;
- next action;
- resume condition;
- last episode summary;
- last N meaningful events;
- active surfaces;
- unresolved blocker/review state.

Output:

```text
WHY THIS EXISTS
WHERE IT IS
WHAT CHANGED
WHY IT STOPPED
WHAT IS UNCERTAIN
FIRST MOVE
RELEVANT SURFACES
```

Later this becomes a provider-neutral **context compiler** for agents.

## 9. Provider-neutral integration layer

Use interfaces such as:

```python
class IntegrationAdapter:
    def identify_surface(...): ...
    def open_surface(...): ...
    def get_status(...): ...
    def dispatch(...): ...
    def ingest_event(...): ...
```

Not every adapter implements every method.

### Antigravity
Current official Antigravity capabilities make deeper integration plausible:

- MCP support can connect agents to Codec tools.
- Plugins can package MCP servers, hooks, skills, and rules.
- The Python SDK supports programmatic autonomous-agent workflows.

Long-term Codec MCP tools might include:

```text
codec.get_thread
codec.begin_episode
codec.record_update
codec.record_blocker
codec.add_artifact
codec.request_review
codec.finish_episode
```

Antigravity should update Codec by reporting **meaningful transitions**, not streaming every log line.

### ChatGPT
V0: save a conversation/project URL as a Surface.

Later options:

- context packet copied/opened into a chosen conversation;
- developer-API Conversations for workflows created by Codec;
- explicit export/import or connector mechanisms if/when supported for the intended surface.

Do not make V0 depend on consumer-ChatGPT history APIs.

## 10. Compute / asynchronous run model

Codec should eventually model machine time explicitly.

Useful properties:

```text
run_status
started_at
expected_duration
last_checkpoint_at
needs_human_at
human_attention_estimate
result_surface
```

This enables latency hiding:

- launch compute;
- work/play elsewhere;
- return only when human action is useful.

V0 can represent this with events and optional expected-duration metadata without building a scheduler.

## 11. Provenance model

Codec should preserve **semantic lineage**, not exhaustive activity logs.

Example:

```text
Source post
  └─SPAWNED_FROM/INSPIRED→ research question
      └─EXPLORED_IN→ ChatGPT surface
          └─PRODUCED→ research report
              └─TRANSFORMS_INTO→ audio
                  └─CONSUMED_IN→ listening episode
                      └─SPAWNED_FROM→ new research thread
```

Avoid recording every click or window switch unless later evidence shows it is useful.

## 12. Security / authority boundary

V0 is local single-user, but future agent actions make authority explicit from the beginning.

Proposed levels:

```text
READ
SUGGEST
PREPARE
EXECUTE_REVERSIBLE
EXECUTE_CONSEQUENTIAL
```

Codec should record which level a work packet/run was granted.

Examples:

- read repository: READ
- propose patch: PREPARE
- edit local branch: EXECUTE_REVERSIBLE
- send calendar invitations / email / deploy production: EXECUTE_CONSEQUENTIAL

Consequential execution should always have explicit policy and adoption/reconciliation behavior.

## 13. Suggested project structure

```text
codec/
├── app.py
├── config.py
├── models.py
├── domain/
│   ├── commands.py
│   ├── transitions.py
│   └── briefings.py
├── routes/
│   ├── cockpit.py
│   ├── threads.py
│   ├── capture.py
│   └── api.py
├── templates/
│   ├── base.html
│   ├── cockpit.html
│   ├── _thread_card.html
│   ├── _thread_drawer.html
│   └── _capture_confirm.html
├── static/
│   ├── codec.css
│   └── codec.js
├── migrations/
├── tests/
└── codec.db
```

## 14. Technical non-goals for V0

- microservices;
- vector database;
- graph database;
- websockets unless needed for a real run-status experiment;
- complex OAuth integrations;
- background orchestration framework;
- custom mobile application;
- automatic browser-history ingestion;
- universal chat scraping;
- autonomous priority engine.

## 15. Current integration references — verified 2026-08-15

- Google Antigravity MCP: https://antigravity.google/docs/mcp
- Google Antigravity SDK overview: https://antigravity.google/docs/sdk/overview
- Google Antigravity plugins: https://antigravity.google/docs/plugins
- Google Antigravity overview: https://antigravity.google/docs/overview
- OpenAI ChatGPT Projects: https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- OpenAI Projects Academy: https://openai.com/academy/projects/
- OpenAI API Conversations reference is exposed in the API documentation: https://platform.openai.com/docs/api-reference
