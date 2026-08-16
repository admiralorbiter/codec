import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from config import Config
from models import Base, Thread, Project, Actor, Event, WorkPacket
from domain.personal_os_scheduler import (
    OperatorState,
    calculate_system_throughput_telemetry,
    schedule_autonomous_batch
)
from mcp_server import CodecMCPServer

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
def seed_os_environment(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="PersonalOS", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    actor_human = Actor(name="Me", actor_type="HUMAN")
    actor_agent = Actor(name="Antigravity", actor_type="AGENT")
    session.add_all([actor_human, actor_agent])
    session.flush()

    # 1. Thread with Prepared Work Packet ready for Autonomous Dispatch
    t1 = Thread(
        project_id=proj.id,
        name="Telemetry Pipeline Optimization",
        intent="Optimize database queries",
        frontier="Packet prepared for background agent",
        state="READY",
        attention_fit="SUPERVISE",
        is_living=True
    )
    session.add(t1)
    session.flush()

    wp1 = WorkPacket(
        thread_id=t1.id,
        desired_outcome="Add indexing to event timestamp queries",
        authority_level="EXECUTE_AND_TEST",
        stop_conditions="Stop if migration breaks backward compatibility",
        status="PREPARED"
    )
    session.add(wp1)

    # 2. Thread with Delivered Work Packet (completed autonomous run)
    t2 = Thread(
        project_id=proj.id,
        name="Context Envelope Benchmark",
        intent="Measure token compression",
        frontier="Evidence delivered",
        state="NEEDS_YOU",
        is_living=True
    )
    session.add(t2)
    session.flush()

    wp2 = WorkPacket(
        thread_id=t2.id,
        desired_outcome="Benchmark compact vs standard profiles",
        status="DELIVERED",
        result_evidence="Benchmarked 5 profiles: 3.2x compression achieved."
    )
    session.add(wp2)

    # 3. Deep Architecture Thread (>6 files changed)
    t3 = Thread(
        project_id=proj.id,
        name="Multi-Agent Kernel Redesign",
        intent="Refactor memory layers",
        frontier="Deep work staged",
        state="READY",
        attention_fit="FOCUS",
        working_set_json=json.dumps({"files_changed_count": 10}),
        is_living=True
    )
    session.add(t3)
    session.commit()

    thread_ids = [t1.id, t2.id, t3.id]
    session.close()
    return thread_ids


def test_system_throughput_telemetry(app_and_db, seed_os_environment):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    telemetry = calculate_system_throughput_telemetry(session)
    assert telemetry["total_living_threads"] == 3
    assert telemetry["packets_delivered"] == 1
    assert telemetry["autonomous_hours_saved"] >= 0.4
    assert "RUNNING" in telemetry["queue_breakdown"]

    session.close()


def test_schedule_autonomous_batch_supervise_mode(app_and_db, seed_os_environment):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    # When operator is SUPERVISING (gaming):
    schedule = schedule_autonomous_batch(session, operator_state="SUPERVISING", available_attention_minutes=15)
    assert schedule["dispatches_count"] == 1
    assert schedule["scheduled_autonomous_dispatches"][0]["thread_name"] == "Telemetry Pipeline Optimization"
    assert schedule["scheduled_autonomous_dispatches"][0]["dispatch_mode"] == "AUTONOMOUS_BACKGROUND"

    # Deep Architecture thread is staged for human dedicated session
    staged_names = [s["thread_name"] for s in schedule["staged_for_human_review"]]
    assert "Multi-Agent Kernel Redesign" in staged_names

    session.close()


def test_mcp_operating_system_tools(app_and_db, seed_os_environment):
    _, db_uri, _ = app_and_db
    server = CodecMCPServer(db_uri=db_uri)

    # 1. Get OS Status
    status = server.get_os_status()
    assert status["total_living_threads"] == 3
    assert status["packets_delivered"] >= 1

    # 2. Schedule Autonomous Batch
    batch = server.schedule_batch(operator_state="OFFLINE_ASLEEP", available_attention_minutes=0)
    assert batch["dispatches_count"] == 1
    assert batch["scheduled_autonomous_dispatches"][0]["authority_level"] == "EXECUTE_AND_TEST"


def test_http_os_endpoints(client, seed_os_environment):
    # GET /api/os/status
    resp_status = client.get("/api/os/status")
    assert resp_status.status_code == 200
    data_status = resp_status.get_json()
    assert data_status["status"] == "ok"
    assert data_status["telemetry"]["total_living_threads"] == 3

    # POST /api/os/schedule-batch
    resp_batch = client.post("/api/os/schedule-batch", json={
        "operator_state": "SUPERVISING",
        "available_attention_minutes": 20
    })
    assert resp_batch.status_code == 200
    data_batch = resp_batch.get_json()
    assert data_batch["status"] == "ok"
    assert data_batch["schedule"]["dispatches_count"] == 1
