import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from config import Config
from seed import seed_database
from models import Thread, WorkPacket
from domain.transitions import (
    create_work_packet,
    dispatch_work_packet,
    deliver_work_packet_result,
    adopt_work_packet_result,
    request_work_packet_rework,
    update_thread_frontier,
    add_thread_relation
)
from domain.git_service import git_commit_working_set, sync_thread_git_working_set
from domain.migrations import run_migrations
from mcp_server import CodecMCPServer

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'

    app = create_app(TestConfig)
    engine = create_engine(TestConfig.SQLALCHEMY_DATABASE_URI)
    seed_database(engine)
    
    app.db_path = db_path
    app.db_uri = TestConfig.SQLALCHEMY_DATABASE_URI
    
    yield app
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session(app):
    engine = create_engine(app.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# 1. Work Packet State Machine Enforcement
def test_work_packet_invalid_transitions(db_session):
    wp = create_work_packet(db_session, thread_id=1, desired_outcome="State machine safety test")
    assert wp.status == "PREPARED"

    # Invalid: Cannot deliver directly from PREPARED (must be DISPATCHED)
    with pytest.raises(ValueError, match="Cannot transition from 'PREPARED' to 'DELIVERED'"):
        deliver_work_packet_result(db_session, wp.id, result_summary="premature delivery")

    # Invalid: Cannot adopt directly from PREPARED
    with pytest.raises(ValueError, match="Cannot transition from 'PREPARED' to 'ACCEPTED'"):
        adopt_work_packet_result(db_session, wp.id)

    # Invalid: Cannot rework from PREPARED
    with pytest.raises(ValueError, match="Cannot transition from 'PREPARED' to 'REWORK_REQUESTED'"):
        request_work_packet_rework(db_session, wp.id, rework_feedback="invalid")

    # Dispatch to DISPATCHED
    dispatch_work_packet(db_session, wp.id, actor_name="Antigravity")
    assert wp.status == "DISPATCHED"

    # Invalid: Cannot adopt directly from DISPATCHED
    with pytest.raises(ValueError, match="Cannot transition from 'DISPATCHED' to 'ACCEPTED'"):
        adopt_work_packet_result(db_session, wp.id)

    # Deliver to DELIVERED
    deliver_work_packet_result(db_session, wp.id, result_summary="Execution finished")
    assert wp.status == "DELIVERED"

    # Request rework -> REWORK_REQUESTED
    request_work_packet_rework(db_session, wp.id, rework_feedback="Needs fixes")
    assert wp.status == "REWORK_REQUESTED"

    # Invalid: Cannot adopt directly from REWORK_REQUESTED without redispatch and redelivery
    with pytest.raises(ValueError, match="Cannot transition from 'REWORK_REQUESTED' to 'ACCEPTED'"):
        adopt_work_packet_result(db_session, wp.id)

# 2. Work Packet Cross-Thread Ownership
def test_work_packet_cross_thread_ownership(db_session):
    wp = create_work_packet(db_session, thread_id=1, desired_outcome="Ownership test")
    dispatch_work_packet(db_session, wp.id)

    # Attempting to deliver packet with wrong thread_id (e.g. thread 2 instead of 1)
    with pytest.raises(ValueError, match="belongs to thread #1, not #2"):
        deliver_work_packet_result(db_session, wp.id, result_summary="Hacked delivery", thread_id=2)

# 3. Target Validation for Thread Relations
def test_relation_target_validation(db_session):
    # Target thread 99999 does not exist
    with pytest.raises(ValueError, match="Target thread #99999 not found"):
        add_thread_relation(db_session, source_id=1, target_id=99999, relation_type="BLOCKS")

# 4. Domain Enum Validation
def test_domain_enum_validation(db_session):
    # Invalid thread state
    with pytest.raises(ValueError, match="Invalid thread state 'INVALID_STATE'"):
        update_thread_frontier(db_session, thread_id=1, state="INVALID_STATE")

    # Invalid attention mode
    with pytest.raises(ValueError, match="Invalid attention mode 'PARTY_MODE'"):
        update_thread_frontier(db_session, thread_id=1, attention_fit="PARTY_MODE")

# 5. Fail-Closed Git Controls
def test_git_commit_fail_closed_on_invalid_repo():
    # Committing on a non-existent or non-git directory fails closed
    res = git_commit_working_set("/non/existent/repo/path", "test commit")
    assert res["status"] == "failed"
    assert "No verified Git repository attached" in res["error"]

def test_git_commit_http_route_rejects_missing_repo(client):
    # Thread 3 in seed database has no verified git repository
    resp = client.post("/threads/3/git-commit", data={"commit_message": "test"}, follow_redirects=False)
    assert resp.status_code == 400
    assert "No verified Git repository attached" in resp.data.decode("utf-8")

# 6. Preserve Human Cognitive Frontier on Git Sync
def test_git_sync_preserves_cognitive_frontier(db_session):
    thread = db_session.query(Thread).filter(Thread.id == 1).first()
    original_frontier = "Human-articulated strategic frontier goal"
    original_action = "Review system architecture with peer agent"
    thread.frontier = original_frontier
    thread.next_action = original_action
    db_session.commit()

    # Sync git working set
    sync_thread_git_working_set(db_session, thread_id=1)
    db_session.refresh(thread)

    # Frontier and next action must NOT be silently overwritten
    assert thread.frontier == original_frontier
    assert thread.next_action == original_action

# 7. SQLite Schema Version Migration Runner
def test_schema_migrations_runner(app):
    applied = run_migrations(app.db_path)
    assert applied >= 0

    # Verify schema_migrations table exists and is populated
    import sqlite3
    conn = sqlite3.connect(app.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT version, description FROM schema_migrations ORDER BY version")
    rows = cursor.fetchall()
    conn.close()

    versions = [r[0] for r in rows]
    assert 1 in versions
    assert 2 in versions

# 8. Cross-Origin Security Protection
def test_origin_header_protection():
    # When app is in non-testing production mode, external origins on POST must be rejected with 403
    class ProdConfig(Config):
        TESTING = False

    prod_app = create_app(ProdConfig)
    prod_client = prod_app.test_client()

    resp = prod_client.post(
        "/api/agent/telemetry",
        json={"thread_id": 1, "step_name": "test"},
        headers={"Origin": "http://malicious-site.com"}
    )
    assert resp.status_code == 403
