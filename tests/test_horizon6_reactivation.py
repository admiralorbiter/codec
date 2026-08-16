import pytest
import os
import tempfile
import json
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from config import Config
from models import Base, Thread, Project, Actor, Event, WorkPacket
from domain.reactivation_engine import (
    ConditionType,
    parse_resume_condition,
    evaluate_thread_resume_condition,
    reactivate_thread,
    check_all_waiting_conditions
)

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


def test_parse_resume_condition():
    # 1. FILE_EXISTS
    c1 = parse_resume_condition("FILE_EXISTS: dist/bundle.js")
    assert c1["type"] == ConditionType.FILE_EXISTS
    assert c1["spec"] == "dist/bundle.js"

    # 2. JSON format
    c2 = parse_resume_condition(json.dumps({"type": "FILE_EXISTS", "path": "output/report.json"}))
    assert c2["type"] == ConditionType.FILE_EXISTS
    assert c2["spec"] == "output/report.json"

    # 3. AGENT_DONE
    c3 = parse_resume_condition("AGENT_DONE")
    assert c3["type"] == ConditionType.AGENT_DONE

    # 4. TIME_ELAPSED
    c4 = parse_resume_condition("TIME_ELAPSED: 60")
    assert c4["type"] == ConditionType.TIME_ELAPSED
    assert c4["spec"] == "60"

    # 5. PROSE fallback
    c5 = parse_resume_condition("Waiting for user to return from dinner")
    assert c5["type"] == ConditionType.PROSE
    assert "dinner" in c5["spec"]


def test_file_exists_reactivation(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="AutoWake", domain="Research", status="ACTIVE")
    session.add(proj)
    session.flush()

    # Create temporary file path
    temp_target = tempfile.mktemp(suffix=".txt")

    t = Thread(
        project_id=proj.id,
        name="Build Artifact Watcher",
        state="WAITING",
        resume_condition=f"FILE_EXISTS: {temp_target}",
        is_living=True
    )
    session.add(t)
    session.commit()

    # 1. Evaluate before file exists -> False
    satisfied, reason = evaluate_thread_resume_condition(t)
    assert not satisfied
    assert "Waiting for file" in reason

    # 2. Create file on disk -> True
    with open(temp_target, "w") as f:
        f.write("artifact ready")

    try:
        satisfied, reason = evaluate_thread_resume_condition(t)
        assert satisfied
        assert "Observed file" in reason

        # 3. Reactivate thread
        reactivated = reactivate_thread(session, t.id, reason)
        assert reactivated.state == "NEEDS_YOU"
        assert "Reactivated" in reactivated.frontier

        # Check braid event
        events = session.query(Event).filter(Event.thread_id == t.id).all()
        assert any(e.event_type == "THREAD_REACTIVATED" for e in events)
    finally:
        if os.path.exists(temp_target):
            os.remove(temp_target)

    session.close()


def test_agent_done_reactivation(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="AgentWatch", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    t = Thread(
        project_id=proj.id,
        name="Agent Run Monitor",
        state="WAITING",
        resume_condition="AGENT_DONE",
        is_living=True
    )
    session.add(t)
    session.flush()

    wp = WorkPacket(
        thread_id=t.id,
        desired_outcome="Compute embedding vectors",
        status="DISPATCHED"
    )
    session.add(wp)
    session.commit()

    # Not done yet
    satisfied, _ = evaluate_thread_resume_condition(t)
    assert not satisfied

    # Agent delivers result
    wp.status = "DELIVERED"
    wp.result_evidence = "Embeddings compiled"
    session.commit()

    satisfied, reason = evaluate_thread_resume_condition(t)
    assert satisfied
    assert "delivered" in reason

    session.close()


def test_check_all_waiting_conditions_batch(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="BatchScan", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    temp_file = tempfile.mktemp(suffix=".done")
    with open(temp_file, "w") as f:
        f.write("done")

    t1 = Thread(
        project_id=proj.id,
        name="Satisfied Thread",
        state="WAITING",
        resume_condition=f"FILE_EXISTS: {temp_file}",
        is_living=True
    )
    t2 = Thread(
        project_id=proj.id,
        name="Unsatisfied Thread",
        state="WAITING",
        resume_condition="FILE_EXISTS: non_existent_file_xyz.bin",
        is_living=True
    )
    session.add_all([t1, t2])
    session.commit()

    try:
        reactivated = check_all_waiting_conditions(session)
        assert len(reactivated) == 1
        assert reactivated[0]["thread_id"] == t1.id

        # Verify t1 is now NEEDS_YOU and t2 remains WAITING
        session.refresh(t1)
        session.refresh(t2)
        assert t1.state == "NEEDS_YOU"
        assert t2.state == "WAITING"
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    session.close()


def test_http_reactivate_endpoints(client, app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="HTTPApi", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    temp_file = tempfile.mktemp(suffix=".tmp")
    with open(temp_file, "w") as f:
        f.write("ready")

    t = Thread(
        project_id=proj.id,
        name="HTTP Reactivate Target",
        state="WAITING",
        resume_condition=f"FILE_EXISTS: {temp_file}",
        is_living=True
    )
    session.add(t)
    session.commit()
    t_id = t.id
    session.close()

    try:
        resp = client.post(f"/threads/{t_id}/reactivate/check")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["reactivated"] is True
        assert data["new_state"] == "NEEDS_YOU"

        # Check-all endpoint
        resp_all = client.post("/cockpit/reactivate/check-all")
        assert resp_all.status_code == 200
        data_all = resp_all.get_json()
        assert data_all["status"] == "ok"
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
