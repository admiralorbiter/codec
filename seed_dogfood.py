import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from models import Base, Project, Actor, Thread, Surface, Episode, Event, Relation, WorkPacket
from domain.git_service import inspect_git_working_set

def seed_dogfood_database(engine=None):
    """Initializes a clean, pristine database for live dogfooding with real active projects."""
    if engine is None:
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)

    # 1. Real Projects
    codec_proj = Project(
        name="Codec",
        description="Personal tactical control plane for human-AI work, living threads, and parallel comms.",
        domain="Research",
        status="ACTIVE",
        created_at=now - timedelta(days=2)
    )
    cod_proj = Project(
        name="Call of Duty & Gaming",
        description="Active recreation and gaming sessions while monitoring background compute and AI agent runs.",
        domain="Personal",
        status="ACTIVE",
        created_at=now - timedelta(hours=4)
    )
    lat_proj = Project(
        name="LAT",
        description="Living Activity Tracker and ingestion pipeline engine.",
        domain="Research",
        status="ACTIVE",
        created_at=now - timedelta(days=14)
    )
    recurrence_proj = Project(
        name="Recurrence",
        description="Recurrence dynamics, persistence effects, and sequence modeling research.",
        domain="Research",
        status="ACTIVE",
        created_at=now - timedelta(days=20)
    )
    polaris_proj = Project(
        name="Polaris",
        description="Core enterprise platform and reporting infrastructure.",
        domain="Professional",
        status="ACTIVE",
        created_at=now - timedelta(days=30)
    )
    big_brain_proj = Project(
        name="Big Brain Time",
        description="Long-memory research transformation into audio, video, and mental models.",
        domain="Creative",
        status="ACTIVE",
        created_at=now - timedelta(days=45)
    )

    session.add_all([codec_proj, cod_proj, lat_proj, recurrence_proj, polaris_proj, big_brain_proj])
    session.flush()

    # 2. Real Actors
    me = Actor(actor_type="HUMAN", name="Me", provider="Human")
    antigravity = Actor(actor_type="AGENT", name="Antigravity", provider="Google")
    chatgpt = Actor(actor_type="AGENT", name="ChatGPT", provider="OpenAI")
    local_compute = Actor(actor_type="PROCESS", name="Local Compute", provider="PyTorch/CUDA")
    external_actor = Actor(actor_type="EXTERNAL_PERSON", name="External Admin", provider="External")
    git_actor = Actor(actor_type="SERVICE", name="Git Engine", provider="Local Git")

    session.add_all([me, antigravity, chatgpt, local_compute, external_actor, git_actor])
    session.flush()

    # 3. Living Threads

    # Thread 1: Codec Tactical Control Plane & Development (CURRENT FOCUS - RUNNING)
    t1_git_info = inspect_git_working_set(".")
    t1_working_set = {
        "repo": "codec",
        "repo_path": "c:/Users/admir/Github/codec",
        "branch": t1_git_info.get("branch", "main"),
        "commit": t1_git_info.get("commit", "head"),
        "files_changed_count": t1_git_info.get("files_changed_count", 0),
        "additions": t1_git_info.get("additions", 0),
        "deletions": t1_git_info.get("deletions", 0),
        "tests_status": "54/54 passing",
        "active_agent": "Antigravity"
    }

    t1 = Thread(
        project_id=codec_proj.id,
        name="Codec Tactical Control Plane & Development",
        intent="Build Codec as a personal mission-control surface for human-AI work, agent dispatch, and attention management.",
        frontier="Horizon 3 & UI Overhaul live with NASA situation strip and semantic braid (54/54 tests passing). Operating in SUPERVISE/gaming mode while preparing Horizon 4 Context Router & Antigravity MCP integration.",
        state="RUNNING",
        attention_fit="SUPERVISE",
        current_actor_id=antigravity.id,
        next_action="Verify Antigravity MCP integration and dispatch Horizon 4 Context Router build packet.",
        resume_condition=None,
        is_living=True,
        is_current_focus=True,
        working_set_json=json.dumps(t1_working_set),
        last_active_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=2)
    )

    # Thread 2: Call of Duty & Evening Gaming (RUNNING)
    t2_working_set = {
        "activity": "Call of Duty Session",
        "attention_profile": "Low Attention / High Latency Tolerance",
        "mode": "Gaming + Background AI Supervision"
    }

    t2 = Thread(
        project_id=cod_proj.id,
        name="Call of Duty & Evening Gaming",
        intent="Active evening gaming session while supervising background AI development runs and local compute.",
        frontier="Active gaming session on primary screen. Codec running on secondary cockpit display for glance supervision and review gates between matches.",
        state="RUNNING",
        attention_fit="CONSUME",
        current_actor_id=me.id,
        next_action="Glance at Codec Radar between matches for review gates and agent adoption checkpoints.",
        resume_condition=None,
        is_living=True,
        is_current_focus=False,
        working_set_json=json.dumps(t2_working_set),
        last_active_at=now - timedelta(minutes=5),
        created_at=now - timedelta(hours=2)
    )

    session.add_all([t1, t2])
    session.flush()

    # 4. Surfaces for Live Threads
    s1 = Surface(
        thread_id=t1.id,
        surface_type="REPOSITORY",
        provider="GitHub",
        label="Repo: Codec Control Plane",
        local_path="c:/Users/admir/Github/codec"
    )
    s2 = Surface(
        thread_id=t1.id,
        surface_type="IDE",
        provider="Antigravity",
        label="Antigravity Dev Session",
        uri="conversation://5578456c-aea6-4df1-a0b8-68d321489e83"
    )

    session.add_all([s1, s2])
    session.flush()

    # 5. Episodes
    ep1 = Episode(
        thread_id=t1.id,
        mode="SUPERVISE",
        summary="Horizon 3 live streaming & UI Overhaul completed with 54 passing tests. Initiating live dogfooding.",
        started_at=now - timedelta(hours=1)
    )
    ep2 = Episode(
        thread_id=t2.id,
        mode="CONSUME",
        summary="Evening gaming session initiated with Codec tactical radar monitoring.",
        started_at=now - timedelta(hours=2)
    )
    session.add_all([ep1, ep2])
    session.flush()

    # 6. Events
    e1 = Event(
        thread_id=t1.id,
        episode_id=ep1.id,
        actor_id=me.id,
        event_type="THREAD_CREATED",
        summary="Initialized Codec Tactical Control Plane live development thread.",
        occurred_at=now - timedelta(hours=3)
    )
    e2 = Event(
        thread_id=t1.id,
        episode_id=ep1.id,
        actor_id=antigravity.id,
        event_type="AGENT_RESULT",
        summary="Completed NASA cockpit UI Overhaul with Situation Strip, semantic braid, and PAIR decision gates (54 tests green).",
        payload_json=json.dumps({
            "checkpoints": [
                {"text": "Persistent Situation Strip integrated and sticky on scroll", "status": "pass"},
                {"text": "Semantic compression applied to activity braid with 1-line routine nodes", "status": "pass"},
                {"text": "PAIR trust calibration added to Decision Gate 2.0 with impact and reversibility", "status": "pass"},
                {"text": "Working set constellation condensed to compact single-line strip", "status": "pass"},
                {"text": "All 54 unit and integration tests passing green", "status": "pass"}
            ]
        }),
        occurred_at=now - timedelta(minutes=15)
    )
    e3 = Event(
        thread_id=t1.id,
        episode_id=ep1.id,
        actor_id=me.id,
        event_type="NOTE",
        summary="Switching to live dogfooding mode while gaming. Antigravity will report updates via MCP.",
        occurred_at=now - timedelta(minutes=2)
    )

    e4 = Event(
        thread_id=t2.id,
        episode_id=ep2.id,
        actor_id=me.id,
        event_type="THREAD_CREATED",
        summary="Gaming session active. Monitoring Codec radar for human intervention checkpoints.",
        occurred_at=now - timedelta(hours=2)
    )

    session.add_all([e1, e2, e3, e4])

    # 7. Semantic Relations
    r1 = Relation(
        source_type="THREAD",
        source_id=t2.id,
        target_type="THREAD",
        target_id=t1.id,
        relation_type="INFORMED_BY",
        note="Gaming session operates under intermittent supervision of background Codec development.",
        created_at=now - timedelta(minutes=5)
    )
    session.add(r1)

    session.commit()
    session.close()
    print("Clean dogfood database initialized with real active threads.")

if __name__ == "__main__":
    seed_dogfood_database()
