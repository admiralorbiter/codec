import pytest
import os
import tempfile
import json
import queue
from sqlalchemy import create_engine
from app import create_app
from config import Config
from seed import seed_database
from domain.sse_service import TelemetryBroadcaster, broadcaster
from domain.transitions import append_event, update_thread_frontier, dispatch_work_packet, create_work_packet
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

def test_telemetry_broadcaster_pubsub():
    tb = TelemetryBroadcaster()
    
    # 1. Global listener
    q_global = tb.subscribe()
    
    # 2. Thread-specific listener
    q_thread7 = tb.subscribe(thread_id=7)
    q_thread1 = tb.subscribe(thread_id=1)
    
    # 3. Broadcast to Thread 7
    tb.broadcast("TEST_EVENT", {"msg": "Hello Thread 7"}, thread_id=7)
    
    # Global receives it
    raw_g = q_global.get_nowait()
    assert "event: TEST_EVENT" in raw_g
    assert "Hello Thread 7" in raw_g
    
    # Thread 7 receives it
    raw_t7 = q_thread7.get_nowait()
    assert "Hello Thread 7" in raw_t7
    
    # Thread 1 should NOT receive it
    with pytest.raises(queue.Empty):
        q_thread1.get_nowait()
        
    # Unsubscribe
    tb.unsubscribe(q_global)
    tb.unsubscribe(q_thread7, thread_id=7)
    tb.unsubscribe(q_thread1, thread_id=1)

def test_agent_telemetry_endpoint(client):
    # Subscribe to broadcaster
    q = broadcaster.subscribe(thread_id=7)
    
    # Send telemetry via POST API
    resp = client.post("/api/agent/telemetry", json={
        "thread_id": 7,
        "step_name": "Running Pytest suite",
        "step_index": 2,
        "total_steps": 4,
        "log_snippet": "PASSED tests/test_cockpit.py",
        "actor_name": "Antigravity"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "broadcasted"
    assert data["telemetry"]["step_name"] == "Running Pytest suite"
    
    # Verify SSE received the broadcast
    raw = q.get(timeout=2.0)
    assert "event: AGENT_TELEMETRY" in raw
    assert "Running Pytest suite" in raw
    assert "PASSED tests/test_cockpit.py" in raw
    
    broadcaster.unsubscribe(q, thread_id=7)

def test_domain_transition_sse_broadcast(app):
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(app.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    q = broadcaster.subscribe(thread_id=1)

    # 1. Append event triggers SSE
    append_event(session, 1, event_type="NOTE", summary="Live SSE telemetry test note")
    raw = q.get(timeout=2.0)
    assert "event: EVENT_APPENDED" in raw
    assert "Live SSE telemetry test note" in raw

    # 2. Update frontier triggers SSE
    update_thread_frontier(session, 1, frontier="Live streaming frontier advance")
    raw2 = q.get(timeout=2.0)
    assert "event: FRONTIER_UPDATED" in raw2
    assert "Live streaming frontier advance" in raw2

    broadcaster.unsubscribe(q, thread_id=1)
    session.close()

def test_mcp_server_telemetry_tools(app):
    server = CodecMCPServer(db_uri=app.db_uri)
    q = broadcaster.subscribe(thread_id=7)

    # 1. Report progress tool
    res = server.report_progress(
        thread_id=7,
        step_name="Refactoring domain models",
        current_step=3,
        total_steps=5,
        log_snippet="Added columns to SQLite schema"
    )
    assert res["status"] == "broadcasted"
    
    raw = q.get(timeout=2.0)
    assert "event: AGENT_TELEMETRY" in raw
    assert "Refactoring domain models" in raw

    # 2. Sync active session tool
    res_sync = server.sync_active_session(
        thread_id=7,
        active_file="domain/sse_service.py",
        current_task="Building TelemetryBroadcaster"
    )
    assert res_sync["status"] == "synced"
    assert res_sync["working_set"]["active_file"] == "domain/sse_service.py"

    broadcaster.unsubscribe(q, thread_id=7)
