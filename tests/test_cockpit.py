import pytest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app import create_app
from models import Base, Thread, Project, Actor, Event, Surface
from seed import seed_database
from config import Config

@pytest.fixture
def app():
    # Use a temporary sqlite file for isolated test runs
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    app = create_app(TestConfig)
    engine = create_engine(TestConfig.SQLALCHEMY_DATABASE_URI)
    seed_database(engine)
    
    yield app
    
    # Cleanup temp db
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def client(app):
    return app.test_client()

def test_cockpit_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "CODEC" in html
    assert "140.85" in html
    assert "NEEDS YOU" in html
    assert "RUNNING" in html
    assert "READY / PREPARED" in html
    assert "WAITING ON CONDITION" in html
    assert "Ingestion Pipeline Refactor" in html
    assert "Persistence Effect" in html

def test_queues_partial(client):
    response = client.get("/queues?mode=SUPERVISE")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "RUNNING" in html
    assert "Persistence Effect" in html

def test_thread_drawer(client):
    response = client.get("/threads/1/drawer")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "CURRENT FRONTIER" in html
    assert "RE-ENTRY BRIEFING CAPSULE" in html
    assert "SURFACES" in html
    assert "RECENT EVENTS" in html

def test_mission_control(client):
    response = client.get("/living")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "MISSION CONTROL" in html
    assert "ALL LIVING THREADS" in html
    assert "Ambient Audio Hooks" in html  # Parked thread visible in mission control

def test_api_threads(client):
    response = client.get("/api/threads")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 5
    assert any(t["name"] == "Ingestion Pipeline Refactor" for t in data)

def test_api_thread_briefing(client):
    response = client.get("/api/threads/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["thread_id"] == 1
    assert "frontier" in data
    assert "why_it_stopped" in data
    assert "first_move" in data
    assert "surfaces" in data
