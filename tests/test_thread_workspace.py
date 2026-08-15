import pytest
import os
import tempfile
from sqlalchemy import create_engine
from app import create_app
from models import Base, Thread, Project, Actor, Event, Surface
from seed import seed_database
from config import Config

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    app = create_app(TestConfig)
    engine = create_engine(TestConfig.SQLALCHEMY_DATABASE_URI)
    seed_database(engine)
    
    yield app
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_thread_workspace_renders_full_braid(client):
    response = client.get("/threads/1")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    # Header and Working Set
    assert "Ingestion Pipeline Refactor" in html
    assert "WORKING SET CONSTELLATION" in html
    assert "feat/lat-ingestion" in html
    assert "18/24 passing" in html
    
    # Activity Braid semantic events
    assert "CHRONOLOGICAL ACTIVITY BRAID" in html
    assert "Dictated implementation strategy" in html
    assert "Created 5-step implementation plan" in html
    assert "Agent Run: Handlers converted" in html
    assert "codec/parser/handler.py" in html
    assert "+143" in html
    assert "-81" in html
    assert "18 Passed" in html
    
    # Decision Gate at the frontier
    assert "DECISION GATE" in html
    assert "SQLite Relational Projection" in html
    assert "Pure Event-Log Replay" in html
    assert "RECOMMENDED" in html
    assert "NOW // CURRENT FRONTIER" in html

def test_decision_gate_resolution(client):
    # Resolve the decision gate on thread 1
    response = client.post("/threads/1/decide", data={
        "choice": "SQLite Relational Projection",
        "reasoning": "Zero replay lag for V0 speed."
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    # Frontier should be updated
    assert "Architecture chosen: SQLite Relational Projection" in html
    assert "Decision made: SQLite Relational Projection" in html

def test_current_focus_switching(client):
    # Check thread 1 is initially focus
    resp = client.get("/threads/1")
    assert "CURRENT FOCUS" in resp.data.decode("utf-8")
    
    # Switch focus to thread 2
    resp2 = client.post("/threads/2/focus", follow_redirects=True)
    assert resp2.status_code == 200
    html2 = resp2.data.decode("utf-8")
    assert "CURRENT FOCUS" in html2
    assert "Persistence Effect" in html2
    
    # Verify thread 1 is no longer active focus
    resp1_after = client.get("/threads/1")
    assert "SET AS CURRENT FOCUS" in resp1_after.data.decode("utf-8")


def test_park_and_resume_flow(client):
    # Park thread 1 with a note
    resp_park = client.post("/threads/1/park", data={
        "note": "Parked after completing handler tests. Resuming tomorrow.",
        "resume_condition": "When database schema migration is finalized"
    }, follow_redirects=True)
    assert resp_park.status_code == 200
    
    # Check thread 1 is parked
    resp_ws = client.get("/threads/1")
    html_ws = resp_ws.data.decode("utf-8")
    assert "RESUME WORK" in html_ws
    assert "Parked thread cleanly" in html_ws or "Parked after completing handler tests" in html_ws
    
    # Resume thread 1
    resp_resume = client.post("/threads/1/resume", follow_redirects=True)
    assert resp_resume.status_code == 200
    html_resumed = resp_resume.data.decode("utf-8")
    assert "CURRENT FOCUS" in html_resumed
    assert "PARK THREAD" in html_resumed

def test_add_custom_event_to_braid(client):
    resp = client.post("/threads/1/events", data={
        "summary": "Completed benchmark run: 1,200 events/sec under 4ms latency.",
        "event_type": "NOTE"
    }, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Completed benchmark run: 1,200 events/sec" in html

def test_cockpit_state_specific_cards(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    
    # Needs you state-specific card
    assert "DECISION GATE" in html
    assert "Architecture Decision Required" in html
    assert "Open Workspace &amp; Decide" in html
    
    # Running state-specific card
    assert "Step 3 / 5" in html
    assert "Executing" in html
    
    # Waiting state-specific card
    assert "WAITING ON:" in html
    assert "Pathful teacher/section CSV export" in html
