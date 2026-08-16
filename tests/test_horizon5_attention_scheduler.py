import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from config import Config
from models import Base, Thread, Project, Actor, Event, WorkPacket
from domain.attention_scheduler import (
    CognitiveLoad,
    estimate_thread_attention_cost,
    filter_and_rank_by_attention
)
from domain.queries import get_cockpit_queues, get_living_threads

@pytest.fixture
def app_and_db():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'

    app = create_app(TestConfig)
    engine = create_engine(TestConfig.SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)

    yield app, TestConfig.SQLALCHEMY_DATABASE_URI, engine

    Base.metadata.drop_all(engine)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

@pytest.fixture
def client(app_and_db):
    app, _, _ = app_and_db
    return app.test_client()

@pytest.fixture
def seed_multi_attention_threads(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="AttentionEngine", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    actor_human = Actor(name="Me", actor_type="HUMAN")
    actor_agent = Actor(name="Antigravity", actor_type="AGENT")
    session.add_all([actor_human, actor_agent])
    session.flush()

    # 1. Running Thread (Glance cost)
    t1 = Thread(
        project_id=proj.id,
        name="Running Agent Task",
        intent="Compile background job",
        frontier="Step 3 executing",
        state="RUNNING",
        attention_fit="SUPERVISE",
        current_actor_id=actor_agent.id,
        is_living=True
    )

    # 2. Delivered Packet (1m Glance Review)
    t2 = Thread(
        project_id=proj.id,
        name="Delivered Work Packet",
        intent="Review evidence",
        frontier="Evidence delivered",
        state="NEEDS_YOU",
        attention_fit="SUPERVISE",
        current_actor_id=actor_human.id,
        is_living=True
    )
    session.add_all([t1, t2])
    session.flush()

    wp = WorkPacket(
        thread_id=t2.id,
        desired_outcome="Refactor telemetry",
        status="DELIVERED",
        result_evidence="All 10 tests green"
    )
    session.add(wp)

    # 3. Decision Required Gate (2-5m Quick Choice)
    t3 = Thread(
        project_id=proj.id,
        name="Decision Fork",
        intent="Select caching layer",
        frontier="Waiting for decision",
        state="NEEDS_YOU",
        attention_fit="FOCUS",
        current_actor_id=actor_human.id,
        is_living=True
    )
    session.add(t3)
    session.flush()

    gate_event = Event(
        thread_id=t3.id,
        actor_id=actor_agent.id,
        event_type="DECISION_REQUIRED",
        summary="Choose between Redis or SQLite",
        payload_json=json.dumps({"options": ["Redis", "SQLite"]})
    )
    session.add(gate_event)

    # 4. Deep Focus Architecture Task (45m+ Deep)
    t4 = Thread(
        project_id=proj.id,
        name="Deep Architecture Refactor",
        intent="Redesign memory layout",
        frontier="Staged for deep weekend session",
        state="READY",
        attention_fit="FOCUS",
        working_set_json=json.dumps({"files_changed_count": 12}),
        is_living=True
    )

    # 5. Audio Briefing (15m Audio Consumption)
    t5 = Thread(
        project_id=proj.id,
        name="Research Paper Digest",
        intent="Listen to paper review",
        frontier="Audio briefing ready",
        state="READY",
        attention_fit="CONSUME",
        is_living=True
    )
    session.add_all([t4, t5])
    session.commit()

    thread_ids = [t1.id, t2.id, t3.id, t4.id, t5.id]
    session.close()
    return thread_ids


def test_cognitive_load_estimation(app_and_db, seed_multi_attention_threads):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    t_ids = seed_multi_attention_threads
    t_running = session.query(Thread).filter(Thread.id == t_ids[0]).first()
    t_delivered = session.query(Thread).filter(Thread.id == t_ids[1]).first()
    t_decision = session.query(Thread).filter(Thread.id == t_ids[2]).first()
    t_deep = session.query(Thread).filter(Thread.id == t_ids[3]).first()
    t_audio = session.query(Thread).filter(Thread.id == t_ids[4]).first()

    # Running thread -> GLANCE (30s)
    c1 = estimate_thread_attention_cost(t_running)
    assert c1["load"] == CognitiveLoad.GLANCE
    assert "30s" in c1["badge_label"]

    # Delivered packet -> GLANCE (1m review)
    c2 = estimate_thread_attention_cost(t_delivered)
    assert c2["load"] == CognitiveLoad.GLANCE
    assert "1m" in c2["badge_label"]

    # Decision Gate -> QUICK_CHOICE (2-5m decision)
    c3 = estimate_thread_attention_cost(t_decision)
    assert c3["load"] == CognitiveLoad.QUICK_CHOICE
    assert "2–5m" in c3["badge_label"]

    # Broad working set (>6 files) -> DEEP_FOCUS (45m+)
    c4 = estimate_thread_attention_cost(t_deep)
    assert c4["load"] == CognitiveLoad.DEEP_FOCUS
    assert "45m+" in c4["badge_label"]

    # CONSUME mode -> AUDIO
    c5 = estimate_thread_attention_cost(t_audio)
    assert c5["load"] == CognitiveLoad.AUDIO_CONSUMPTION
    assert "Audio" in c5["badge_label"]

    session.close()


def test_supervise_mode_stages_deep_work(app_and_db, seed_multi_attention_threads):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    threads = session.query(Thread).all()
    sliced = filter_and_rank_by_attention(threads, mode="SUPERVISE")

    # In SUPERVISE mode, the Deep Focus thread (t4) should be staged in staged_deep_work
    staged_names = [t.name for t in sliced["staged_deep_work"]]
    active_names = [t.name for t in sliced["active_threads"]]

    assert "Deep Architecture Refactor" in staged_names
    assert "Running Agent Task" in active_names
    assert "Delivered Work Packet" in active_names
    assert sliced["staged_count"] == 1

    session.close()


def test_cockpit_queues_with_staging_and_http(client, seed_multi_attention_threads):
    # Test HTTP GET /queues?mode=SUPERVISE
    resp = client.get("/queues?mode=SUPERVISE")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "DEEP-WORK STAGING BUFFER" in html
    assert "Deep Architecture Refactor" in html
    assert "badge-cog" in html
