# Codec

> A personal control plane for human–AI work.

**Status:** V0 Live Dogfood Build  
**Date:** 2026-08-15  
**Design target:** immediate weekend dogfooding (Frequency: `140.85`)

Codec is a low-friction, voice-friendly system for managing **living threads of work** across projects, tools, agents, computation, research, waiting states, and personal life.

It is deliberately **not** a conventional project manager. The primary object is not a task with a due date; it is a **thread with a frontier**: where the work currently is, who or what has the ball, what is needed next, and how to re-enter with minimal cognitive reconstruction.

The name is a deliberate Metal Gear Solid reference. In Konami's MGS2 manual, the Codec is the communication surface through which the player contacts mission support and gets mission-relevant information. Codec-the-project borrows that mission-control metaphor, not the game's fiction or branding.

---

## Quickstart

### 1. Install & Run
```powershell
# Start local server
python app.py
```
Open **http://127.0.0.1:5050** in your browser.

### 2. Database Management
- **Seed with rich demo data (LAT, Recurrence, Polaris, Big Brain, Side-Tracked):**
  ```powershell
  python seed.py
  ```
- **Reset to a clean slate:**
  ```powershell
  python -c "from config import Config; from models import Base; from sqlalchemy import create_engine; engine = create_engine(Config.SQLALCHEMY_DATABASE_URI); Base.metadata.drop_all(engine); Base.metadata.create_all(engine); print('Database reset to clean slate.')"
  ```

### 3. Run Automated Tests
```powershell
python -m pytest
```

### 4. Antigravity MCP Server
Codec includes a standalone Model Context Protocol server exposing control plane tools for Antigravity AI agents:
```powershell
python mcp_server.py
```

---

## Core Views

1. **Radar / Attention Queues (`/`)**: Grouped by human cognitive relationship: `NEEDS YOU`, `RUNNING`, `READY`, and `WAITING ON CONDITION`.
2. **Parallel Comms Matrix (`/parallel`)**: 2-Split, 3-Triad, and 4-Matrix multi-channel cockpit for supervising concurrent agent runs and compute jobs while actively reasoning.
3. **Mission Control (`/living`)**: High-density table of all living threads across domains with slide-out drawer integration.
4. **Thread Dedicated Workspace (`/threads/<id>`)**: Working Set Constellation, Chronological Activity Braid, Decision Gates, and Re-entry Briefing Capsule.
5. **Universal Voice Capture (`🎙 CAPTURE`)**: 1-click browser speech recognition (Web Speech API) with live heuristic transition parsing and commit.

---

## Planning Pack & Architecture Docs

1. [Vision & Product Principles](docs/01_VISION_AND_PRINCIPLES.md)
2. [UX / UI Specification](docs/02_UX_UI_SPEC.md)
3. [System Architecture & Data Model](docs/03_SYSTEM_ARCHITECTURE.md)
4. [V0 Weekend Build Plan](docs/04_V0_WEEKEND_BUILD_PLAN.md)
5. [Research Basis & Long-Term Roadmap](docs/05_RESEARCH_AND_ROADMAP.md)

---

## Metal Gear Flavor Guide

- **Codec** — the system
- **Radar** — live attention queue cockpit (`140.85`)
- **Parallel Comms** — multi-channel frequency matrix (`140.96`, `141.12`, `141.80`)
- **Mission Control** — full living-thread overview
- **Briefing** — resume capsule / context packet
- **Shadow Moses test** — the first serious dogfood test: can the system survive a messy real weekend without becoming bureaucracy?

> “A strong man doesn't need to read the future. He makes his own.” — Solid Snake, *Metal Gear Solid*

