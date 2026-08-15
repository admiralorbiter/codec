# Codec

> A personal control plane for human–AI work.

**Status:** V0 planning pack  
**Date:** 2026-08-15  
**Design target:** immediate weekend dogfooding

Codec is a low-friction, voice-friendly system for managing **living threads of work** across projects, tools, agents, computation, research, waiting states, and personal life.

It is deliberately **not** a conventional project manager. The primary object is not a task with a due date; it is a **thread with a frontier**: where the work currently is, who or what has the ball, what is needed next, and how to re-enter with minimal cognitive reconstruction.

The name is a deliberate Metal Gear Solid reference. In Konami's MGS2 manual, the Codec is the communication surface through which the player contacts mission support and gets mission-relevant information. Codec-the-project borrows that mission-control metaphor, not the game's fiction or branding.

## Planning pack

1. [Vision & Product Principles](01_VISION_AND_PRINCIPLES.md)
2. [UX / UI Specification](02_UX_UI_SPEC.md)
3. [System Architecture & Data Model](03_SYSTEM_ARCHITECTURE.md)
4. [V0 Weekend Build Plan](04_V0_WEEKEND_BUILD_PLAN.md)
5. [Research Basis & Long-Term Roadmap](05_RESEARCH_AND_ROADMAP.md)

## One-sentence product definition

**Codec tracks the state of ongoing human–machine activity and helps route the right work to the right kind of attention at the right time.**

## V0 hypothesis

If Codec can make these three moments substantially easier, it is worth continuing:

1. **Leaving work** — parking a thread without losing the mental state.
2. **Returning to work** — reconstructing the frontier in seconds rather than minutes.
3. **Operating multiple threads** — seeing what needs deep thought, what can be delegated, what is running, and what is merely waiting.

## Non-goals for V0

- Jira replacement
- automated life optimization
- generalized multi-user project management
- full agent orchestration
- automatic ingestion of every chat, file, browser action, or keystroke
- a graph visualization as the primary UI
- elaborate priority scoring

## Metal Gear flavor guide

References should stay light and useful. A few internal labels are fun; the application should never require familiarity with Metal Gear.

Possible internal codenames:

- **Codec** — the system
- **Mission Control** — full living-thread overview
- **Briefing** — resume capsule / context packet
- **Intel** — provenance and research lineage
- **Dispatch** — work prepared for an agent or compute process
- **Shadow Moses test** — the first serious dogfood test: can the system survive a messy real weekend without becoming bureaucracy?

One line worth keeping near the project, because it captures the product philosophy surprisingly well:

> “A strong man doesn't need to read the future. He makes his own.” — Solid Snake, *Metal Gear Solid*

Codec should help prepare the future, not pretend it can perfectly predict it.

## Immediate success criterion

By the end of the first dogfood cycle, Codec should feel faster than the notebook/window-management workflow it replaces. If maintaining Codec feels like work, the design is wrong.

---

### Naming reference

- Konami, *METAL GEAR SOLID 2: Sons of Liberty* online manual — Codec description: https://metalgear.konami.net/manual/mc1/mgs2/xbox/en/page07.html
- Quote reference: https://www.imdb.com/title/tt0180825/quotes/?item=qt0396715
