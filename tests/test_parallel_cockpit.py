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

def test_parallel_cockpit_default_3_triad(client):
    response = client.get("/parallel")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    # Header and Matrix tags
    assert "PARALLEL CODEC COMMS MATRIX" in html
    assert "grid-cols-3" in html
    
    # 3 Channels rendered with frequencies
    assert "CH 1 // 140.85" in html
    assert "CH 2 // 140.96" in html
    assert "CH 3 // 141.12" in html
    
    # Living thread activity braids in parallel
    assert "Ingestion Pipeline Refactor" in html
    assert "Persistence Effect" in html
    assert "Teacher Dashboard" in html

def test_parallel_cockpit_column_variants(client):
    # Test 2-Split layout
    resp_2 = client.get("/parallel?cols=2")
    assert resp_2.status_code == 200
    html_2 = resp_2.data.decode("utf-8")
    assert "grid-cols-2" in html_2
    assert "CH 1 // 140.85" in html_2
    assert "CH 2 // 140.96" in html_2

    # Test 4-Matrix layout
    resp_4 = client.get("/parallel?cols=4")
    assert resp_4.status_code == 200
    html_4 = resp_4.data.decode("utf-8")
    assert "grid-cols-4" in html_4
    assert "CH 4 // 141.80" in html_4

def test_channel_pane_partial(client):
    response = client.get("/channels/1/thread/1")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "channel-pane" in html
    assert "CH 1 // 140.85" in html
    assert "Ingestion Pipeline Refactor" in html
    assert "DECISION REQUIRED" in html or "DECISION GATE" in html or "DECISION" in html

def test_in_pane_decision_resolution(client):
    response = client.post("/channels/1/thread/1/decide", data={
        "choice": "SQLite Relational Projection",
        "reasoning": "Decided in-pane from Channel 1."
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    # Channel 1 partial should show updated frontier
    assert "Architecture chosen: SQLite Relational Projection" in html
    assert "Decision made: SQLite Relational Projection" in html

def test_in_pane_event_appending(client):
    response = client.post("/channels/2/thread/2/events", data={
        "summary": "GPU epoch 45 checkpoint verified (loss down to 0.12).",
        "event_type": "AGENT_CHECKPOINT"
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    assert "GPU epoch 45 checkpoint verified" in html
    assert "CH 2 // 140.96" in html

def test_in_pane_park_and_resume(client):
    # Park thread 1 in Channel 1
    resp_park = client.post("/channels/1/thread/1/park", data={
        "note": "Parked directly inside Channel 1 pane."
    }, follow_redirects=True)
    assert resp_park.status_code == 200
    html_park = resp_park.data.decode("utf-8")
    assert "PARKED" in html_park
    assert "▶ Resume" in html_park

    # Resume thread 1 in Channel 1
    resp_resume = client.post("/channels/1/thread/1/resume", follow_redirects=True)
    assert resp_resume.status_code == 200
    html_resume = resp_resume.data.decode("utf-8")
    assert "⏹ Park" in html_resume
