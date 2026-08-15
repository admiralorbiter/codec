import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from models import Base, Project, Actor, Thread, Surface, Episode, Event, Relation, WorkPacket

def seed_database(engine=None):
    if engine is None:
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)

    # 1. Projects
    codec_proj = Project(
        name="Codec",
        description="Personal tactical control plane for human-AI work, living threads, and parallel comms.",
        domain="Research",
        status="ACTIVE",
        created_at=now - timedelta(days=2)
    )
    lat = Project(
        name="LAT",
        description="Living Activity Tracker and ingestion pipeline engine.",
        domain="Research",
        status="ACTIVE",
        created_at=now - timedelta(days=14)
    )
    polaris = Project(
        name="Polaris",
        description="Core enterprise platform and reporting infrastructure.",
        domain="Professional",
        status="ACTIVE",
        created_at=now - timedelta(days=30)
    )
    recurrence = Project(
        name="Recurrence",
        description="Recurrence dynamics, persistence effects, and sequence modeling research.",
        domain="Research",
        status="ACTIVE",
        created_at=now - timedelta(days=20)
    )
    big_brain = Project(
        name="Big Brain Time",
        description="Long-memory research transformation into audio, video, and mental models.",
        domain="Creative",
        status="ACTIVE",
        created_at=now - timedelta(days=45)
    )
    sidetracked = Project(
        name="Side-Tracked",
        description="Lightweight activity and ambient context logger.",
        domain="Personal",
        status="ACTIVE",
        created_at=now - timedelta(days=10)
    )

    session.add_all([codec_proj, lat, polaris, recurrence, big_brain, sidetracked])
    session.flush()

    # 2. Actors
    me = Actor(actor_type="HUMAN", name="Me", provider="Human")
    antigravity = Actor(actor_type="AGENT", name="Antigravity", provider="Google")
    chatgpt = Actor(actor_type="AGENT", name="ChatGPT", provider="OpenAI")
    local_compute = Actor(actor_type="PROCESS", name="Local Compute", provider="PyTorch/CUDA")
    external_admin = Actor(actor_type="EXTERNAL_PERSON", name="District Admin", provider="Pathful")
    git_actor = Actor(actor_type="SERVICE", name="Git Engine", provider="Local Git")

    session.add_all([me, antigravity, chatgpt, local_compute, external_admin, git_actor])
    session.flush()

    # 3. Threads
    # Thread 1: LAT Refactor (NEEDS_YOU - CURRENT FOCUS)
    t1_working_set = {
        "repo": "LAT Engine",
        "repo_path": ".",
        "branch": "feat/lat-ingestion",
        "commit": "a8f309b",
        "files_changed_count": 5,
        "additions": 235,
        "deletions": 81,
        "tests_status": "18/24 passing",
        "active_agent": "Antigravity",
        "artifacts_count": 3
    }
    t1 = Thread(
        project_id=lat.id,
        name="Ingestion Pipeline Refactor",
        intent="Refactor raw event ingestion to support high-throughput event logging with low UI latency.",
        frontier="Agent completed parser handler conversion. Found 2 competing storage approaches (event-sourced replay vs SQLite relational projection). Awaiting architecture decision.",
        state="NEEDS_YOU",
        attention_fit="INTERACTIVE",
        current_actor_id=antigravity.id,
        next_action="Choose SQLite relational projection over event log replay for V0 speed.",
        is_living=True,
        is_current_focus=True,
        working_set_json=json.dumps(t1_working_set),
        last_active_at=now - timedelta(minutes=6),
        created_at=now - timedelta(days=2)
    )

    # Thread 2: Recurrence Research (RUNNING)
    t2_working_set = {
        "repo": "Recurrence",
        "repo_path": "c:/Users/admir/Github/recurrence",
        "branch": "main",
        "commit": "c4d291e",
        "compute_pid": 4082,
        "expected_duration": "35 min",
        "elapsed": "24 min"
    }
    t2 = Thread(
        project_id=recurrence.id,
        name="Persistence Effect & Baseline Run",
        intent="Evaluate whether memory recurrence persists across phase shifts against a randomized baseline.",
        frontier="Initial persistence effect observed in trial #1. Running 100-epoch shuffled baseline on GPU to verify statistical significance.",
        state="RUNNING",
        attention_fit="SUPERVISE",
        current_actor_id=local_compute.id,
        next_action="Compare baseline output distribution with trial #1 upon process completion.",
        resume_condition="When shuffled baseline run completes (est. 11m remaining)",
        is_living=True,
        is_current_focus=False,
        working_set_json=json.dumps(t2_working_set),
        last_active_at=now - timedelta(minutes=24),
        created_at=now - timedelta(days=3)
    )

    # Thread 3: Teacher Dashboard (WAITING)
    t3 = Thread(
        project_id=polaris.id,
        name="Teacher Dashboard Import Validation",
        intent="Validate import parser and section mapper on real district roster data.",
        frontier="Dashboard implementation works on sample fixtures. Real-data validation is paused waiting on the Pathful export file.",
        state="WAITING",
        attention_fit="FOCUS",
        current_actor_id=external_admin.id,
        next_action="Run validation script against Pathful export and inspect unmapped teacher IDs.",
        resume_condition="When Pathful teacher/section CSV export arrives via email",
        is_living=True,
        is_current_focus=False,
        last_active_at=now - timedelta(hours=3),
        created_at=now - timedelta(days=5)
    )

    # Thread 4: Mechanics Learning (READY - CONSUME)
    t4 = Thread(
        project_id=big_brain.id,
        name="Classical Mechanics Audio Synthesis",
        intent="Transform complex Hamiltonian mechanics lecture series into 18-minute synthesized audio overview for walking reflection.",
        frontier="Audio synthesis complete (18m). Prepared for focused listening episode to extract 2 core paradoxes.",
        state="READY",
        attention_fit="CONSUME",
        current_actor_id=me.id,
        next_action="Listen to audio podcast on headphones and note core Hamiltonian invariants.",
        is_living=True,
        is_current_focus=False,
        last_active_at=now - timedelta(hours=5),
        created_at=now - timedelta(days=1)
    )

    # Thread 5: Polaris Work Packet (READY - FOCUS)
    t5 = Thread(
        project_id=polaris.id,
        name="Automated Regression Harness",
        intent="Create automated end-to-end regression tests across all district report endpoints.",
        frontier="Work packet specifications and stop-conditions fully drafted. Ready for agent dispatch with reversible execution authority.",
        state="READY",
        attention_fit="FOCUS",
        current_actor_id=antigravity.id,
        next_action="Dispatch work packet to Antigravity agent in isolated branch.",
        is_living=True,
        is_current_focus=False,
        last_active_at=now - timedelta(hours=8),
        created_at=now - timedelta(days=4)
    )

    # Thread 6: Side-Tracked (PARKED)
    t6 = Thread(
        project_id=sidetracked.id,
        name="Ambient Audio Hooks",
        intent="Capture ambient voice triggers and pipe into local transcription buffer.",
        frontier="Audio capture pipeline working on local test device. Parked cleanly to focus on Codec V0 cockpit dogfooding.",
        state="PARKED",
        attention_fit="INTERACTIVE",
        current_actor_id=me.id,
        next_action="Resume when Codec V0 dogfood weekend test completes.",
        resume_condition="After Codec V0 dogfood test completes",
        is_living=False,
        is_current_focus=False,
        last_active_at=now - timedelta(days=2),
        created_at=now - timedelta(days=8)
    )

    # Thread 7: Codec Tactical Control Plane (READY - FOCUS)
    t7_working_set = {
        "repo": "codec",
        "repo_path": ".",
        "branch": "main",
        "commit": "1f274b2",
        "files_changed_count": 8,
        "additions": 340,
        "deletions": 45,
        "tests_status": "35/35 passing",
        "active_agent": "Antigravity"
    }
    t7 = Thread(
        project_id=codec_proj.id,
        name="Codec Tactical Control Plane & Horizon 1 Engine",
        intent="Build a low-friction, voice-friendly personal control plane for human-AI work with live Git working sets and attention-aware queues.",
        frontier="Horizon 1 implemented (Live Git Sync, AI Context Packet, Decision Gate, Cross-Thread Relations). 35/35 tests passing. Verifying live Git sync on Codec repository.",
        state="READY",
        attention_fit="FOCUS",
        current_actor_id=antigravity.id,
        next_action="Perform live Git sync test and verify uncommitted working tree diff stats.",
        is_living=True,
        is_current_focus=False,
        working_set_json=json.dumps(t7_working_set),
        last_active_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=2)
    )

    session.add_all([t1, t2, t3, t4, t5, t6, t7])
    session.flush()

    # 4. Surfaces
    s1 = Surface(thread_id=t1.id, surface_type="CHAT", provider="Antigravity", label="Antigravity Refactor Session", uri="conversation://lat-refactor")
    s2 = Surface(thread_id=t1.id, surface_type="REPOSITORY", provider="GitHub", label="Repo: LAT Engine", local_path=".")
    s3 = Surface(thread_id=t1.id, surface_type="BRANCH", provider="Git", label="branch: feat/lat-ingestion")
    s3b = Surface(thread_id=t1.id, surface_type="CHAT", provider="ChatGPT", label="ChatGPT Persistence Architecture Thread", uri="https://chatgpt.com/g/p-lat-arch")

    s4 = Surface(thread_id=t2.id, surface_type="NOTEBOOK", provider="Local", label="persistence_eval.ipynb", local_path="c:/Users/admir/Github/recurrence/notebooks/persistence_eval.ipynb")
    s5 = Surface(thread_id=t2.id, surface_type="TERMINAL", provider="PyTorch", label="GPU Run #4082 (shuffled baseline)")

    s6 = Surface(thread_id=t3.id, surface_type="WEBPAGE", provider="Pathful", label="Pathful Export Portal", uri="https://pathful.com/export/dashboard")
    s7 = Surface(thread_id=t3.id, surface_type="BRANCH", provider="Git", label="branch: polaris/teacher-dash")

    s8 = Surface(thread_id=t4.id, surface_type="AUDIO", provider="Local", label="mechanics_synthesis_ep04.mp3", local_path="c:/Users/admir/Audio/mechanics_synthesis_ep04.mp3")
    s9 = Surface(thread_id=t5.id, surface_type="IDE", provider="Antigravity", label="Polaris Workspace", local_path="c:/Users/admir/Github/polaris")
    s10 = Surface(thread_id=t5.id, surface_type="CHAT", provider="ChatGPT", label="ChatGPT Polaris Architecture Project", uri="https://chatgpt.com/g/p-polaris-planning")

    s11 = Surface(thread_id=t7.id, surface_type="REPOSITORY", provider="GitHub", label="Repo: Codec Control Plane", local_path=".")
    s12 = Surface(thread_id=t7.id, surface_type="IDE", provider="Antigravity", label="Antigravity Pair-Programming Workspace", uri="conversation://codec-dev")

    session.add_all([s1, s2, s3, s3b, s4, s5, s6, s7, s8, s9, s10, s11, s12])
    session.flush()

    # 4b. Sample Work Packets (Horizon 2)
    wp1 = WorkPacket(
        thread_id=t1.id,
        desired_outcome="Refactor raw event ingestion handler with bounded memory queue",
        constraints="Preserve backward-compatible SQLite schema",
        stop_conditions="Stop if test failure count > 1 or before modifying database migration files",
        authority_level="EXECUTE_AND_TEST",
        expected_evidence="Passing test suite (18/24 passing) and git working set diff",
        review_requirement="MANDATORY_HUMAN_REVIEW",
        status="DELIVERED",
        result_summary="Completed parser handler refactor with fast SQLite projection",
        result_evidence="PASSED tests/test_cockpit.py\nPASSED tests/test_thread_workspace.py\nDiff: +235/-81 across 5 files",
        created_at=now - timedelta(hours=2),
        dispatched_at=now - timedelta(hours=1, minutes=45),
        completed_at=now - timedelta(minutes=6)
    )

    wp7 = WorkPacket(
        thread_id=t7.id,
        desired_outcome="Build Horizon 2 Work Packet schema, test suite, and UI adoption lifecycle",
        constraints="Do not modify core database models without migrations; keep backwards compatibility",
        stop_conditions="Stop if unit test failures > 0",
        authority_level="EXECUTE_AND_TEST",
        expected_evidence="Passing pytest suite (41+ tests) and clean git working set",
        review_requirement="MANDATORY_HUMAN_REVIEW",
        status="PREPARED",
        created_at=now - timedelta(minutes=10)
    )

    session.add_all([wp1, wp7])
    session.flush()

    # 5. Events / Chronological Activity Braid for Thread 1 (LAT Refactor)
    e1_genesis = Event(
        thread_id=t1.id,
        event_type="THREAD_CREATED",
        summary="Thread initialized for ingestion pipeline refactoring.",
        actor_id=me.id,
        occurred_at=now - timedelta(hours=3)
    )

    e1_voice = Event(
        thread_id=t1.id,
        event_type="VOICE_NOTE",
        summary="🎙 Dictated implementation strategy for parser handler migration.",
        payload_json=json.dumps({
            "transcript": "Let's refactor the raw ingestion handlers first to decouple SQLite projections from streaming event logs. Keep memory latency under 5ms.",
            "audio_duration": "0:42"
        }),
        actor_id=me.id,
        occurred_at=now - timedelta(minutes=56)
    )

    e1_plan = Event(
        thread_id=t1.id,
        event_type="PLAN",
        summary="Created 5-step implementation plan for ingestion refactor.",
        payload_json=json.dumps({
            "plan_title": "Ingestion Pipeline Refactor",
            "steps": [
                {"step": 1, "title": "Inspect parser boundary handlers", "status": "COMPLETED"},
                {"step": 2, "title": "Convert handler to async batch dispatcher", "status": "COMPLETED"},
                {"step": 3, "title": "Run SQLite migration regression tests", "status": "COMPLETED"},
                {"step": 4, "title": "Resolve storage architecture (relational vs event-replay)", "status": "ACTIVE"},
                {"step": 5, "title": "Benchmark throughput under load", "status": "PENDING"}
            ]
        }),
        actor_id=antigravity.id,
        occurred_at=now - timedelta(minutes=48)
    )

    e1_checkpoints = Event(
        thread_id=t1.id,
        event_type="AGENT_CHECKPOINT",
        summary="Agent Run: Handlers converted, tests executed, competing strategies found.",
        payload_json=json.dumps({
            "checkpoints": [
                {"status": "pass", "text": "Parser handler conversion completed cleanly"},
                {"status": "pass", "text": "Unit tests executed (18/24 passed)"},
                {"status": "warn", "text": "Discovered competing persistence strategies: pure event-replay creates 40ms replay overhead vs instant SQLite projection"}
            ]
        }),
        actor_id=antigravity.id,
        occurred_at=now - timedelta(minutes=35)
    )

    e1_git = Event(
        thread_id=t1.id,
        event_type="GIT_DIFF",
        summary="Git working set updated (+235 / -81 lines across 5 files).",
        payload_json=json.dumps({
            "branch": "feat/lat-ingestion",
            "commit": "a8f309b",
            "files": [
                {"path": "codec/parser/handler.py", "additions": 143, "deletions": 81},
                {"path": "codec/storage/models.py", "additions": 92, "deletions": 0}
            ]
        }),
        actor_id=git_actor.id,
        occurred_at=now - timedelta(minutes=22)
    )

    e1_test = Event(
        thread_id=t1.id,
        event_type="TEST_RESULT",
        summary="18/24 unit tests passing. 6 migration tests awaiting storage choice.",
        payload_json=json.dumps({
            "passed": 18,
            "failed": 0,
            "pending": 6,
            "suite": "tests/test_ingestion.py"
        }),
        actor_id=antigravity.id,
        occurred_at=now - timedelta(minutes=15)
    )

    e1_decision_gate = Event(
        thread_id=t1.id,
        event_type="DECISION_REQUIRED",
        summary="DECISION GATE: Choose persistence architecture.",
        payload_json=json.dumps({
            "decision_title": "Choose Persistence Architecture",
            "need_type": "DECISION",
            "estimated_attention": "2–5 min",
            "options": [
                {
                    "id": "sqlite_proj",
                    "title": "SQLite Relational Projection",
                    "description": "Single-table projection with fast indexed lookups. Zero replay lag, ideal for V0 weekend build.",
                    "recommended": True
                },
                {
                    "id": "event_replay",
                    "title": "Pure Event-Log Replay",
                    "description": "Strict event sourcing with on-the-fly state reconstruction. Higher audit fidelity but 40ms cold-start lag.",
                    "recommended": False
                }
            ]
        }),
        actor_id=antigravity.id,
        occurred_at=now - timedelta(minutes=6)
    )

    session.add_all([e1_genesis, e1_voice, e1_plan, e1_checkpoints, e1_git, e1_test, e1_decision_gate])

    # Events for other threads
    e2_1 = Event(thread_id=t2.id, event_type="DISCOVERY", summary="Persistence effect observed in trial #1 (p < 0.01 preliminary).", actor_id=me.id, occurred_at=now - timedelta(hours=1))
    e2_2 = Event(thread_id=t2.id, event_type="COMPUTE_STARTED", summary="Shuffled baseline run started on local GPU / process #4082 (est. 35m).", payload_json=json.dumps({"pid": 4082, "epochs": 100, "elapsed_min": 24, "remaining_min": 11, "step_current": 3, "step_total": 5}), actor_id=local_compute.id, occurred_at=now - timedelta(minutes=24))

    e3_1 = Event(thread_id=t3.id, event_type="NOTE", summary="Sample synthetic fixtures validated successfully.", actor_id=me.id, occurred_at=now - timedelta(hours=6))
    e3_2 = Event(thread_id=t3.id, event_type="WAITING", summary="Waiting on real Pathful teacher CSV export from district admin.", payload_json=json.dumps({"waiting_on": "Pathful teacher export", "when": "new export arrives", "then": "run validation and inspect unmapped teacher IDs"}), actor_id=me.id, occurred_at=now - timedelta(hours=3))

    e4_1 = Event(thread_id=t4.id, event_type="DISCOVERY", summary="Synthesized core Hamiltonian invariant principles.", actor_id=me.id, occurred_at=now - timedelta(hours=6))
    e4_2 = Event(thread_id=t4.id, event_type="ARTIFACT", summary="Generated podcast audio track (18m) ready for listening episode.", payload_json=json.dumps({"media_type": "audio", "duration": "18m", "title": "Classical Mechanics Synthesis"}), actor_id=me.id, occurred_at=now - timedelta(hours=5))

    session.add_all([e2_1, e2_2, e3_1, e3_2, e4_1, e4_2])

    # 6. Episodes
    ep1 = Episode(thread_id=t1.id, started_at=now - timedelta(hours=3), mode="INTERACTIVE", summary="Handler migration in progress; reached decision gate.")
    ep2 = Episode(thread_id=t2.id, started_at=now - timedelta(hours=1), mode="SUPERVISE", summary="Observed persistence effect, kicked off shuffled baseline GPU compute.")
    ep3 = Episode(thread_id=t3.id, started_at=now - timedelta(hours=6), ended_at=now - timedelta(hours=3), mode="FOCUS", summary="Sample data validated.", ending_reason="Waiting for Pathful export.")

    session.add_all([ep1, ep2, ep3])

    session.commit()
    session.close()
    print("Database seeded with rich activity braids and working sets.")

if __name__ == "__main__":
    seed_database()
