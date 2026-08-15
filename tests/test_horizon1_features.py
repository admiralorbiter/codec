import pytest
import os
import tempfile
import json
from datetime import timedelta
from sqlalchemy import create_engine
from app import create_app
from config import Config
from seed import seed_database
from domain.git_service import inspect_git_working_set, sync_thread_git_working_set
from domain.queries import compile_ai_context_packet, get_thread_by_id, get_thread_relations
from models import Thread, utcnow

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

def test_git_sync_endpoint(client, app):
    ws = inspect_git_working_set('.')
    assert ws.get('branch') is not None
    assert 'files_changed_count' in ws

    resp = client.post('/threads/1/git-sync', headers={'HX-Request': 'true'})
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'WORKING SET' in html

def test_ai_context_packet(client, app):
    resp = client.get('/threads/1/context-packet')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert 'MISSION CONTEXT' in data['packet']
    assert 'Primary Intent' in data['packet']

def test_decision_gate_creation(client, app):
    resp = client.post('/threads/1/decision-gate', data={
        'title': 'Choose Message Broker',
        'opt1_title': 'RabbitMQ',
        'opt1_desc': 'AMQP standard, strong guarantees',
        'opt2_title': 'Redis Streams',
        'opt2_desc': 'Lightweight, already in stack',
        'recommended': '2',
        'attention': '2-5 min'
    }, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Choose Message Broker' in html
    assert 'Redis Streams' in html

def test_relations_crud(client, app):
    resp_add = client.post('/threads/1/relations', data={
        'target_id': 2,
        'relation_type': 'DEPENDS_ON',
        'note': 'Requires baseline export first'
    }, follow_redirects=True)
    assert resp_add.status_code == 200
    html = resp_add.data.decode('utf-8')
    assert 'DEPENDS_ON' in html

    resp_del = client.post('/relations/1/delete', data={'thread_id': 1}, follow_redirects=True)
    assert resp_del.status_code == 200

def test_stale_frontier_detection(app):
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(app.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    thread = session.query(Thread).filter(Thread.id == 1).first()
    assert thread.is_stale_frontier == False

    thread.last_active_at = utcnow() - timedelta(days=4)
    session.commit()
    session.refresh(thread)
    assert thread.is_stale_frontier == True

    thread.state = 'PARKED'
    thread.last_active_at = utcnow() - timedelta(days=8)
    session.commit()
    session.refresh(thread)
    assert thread.is_cold_storage == True

    session.close()

def test_git_commit_endpoint(client, app, monkeypatch):
    import domain.git_service
    def mock_commit(repo_path, commit_message, do_push=False):
        return {"status": "success", "commit": "mock123", "message": commit_message, "pushed": False}
    monkeypatch.setattr(domain.git_service, "git_commit_working_set", mock_commit)
    monkeypatch.setattr("app.git_commit_working_set", mock_commit)

    resp = client.post('/threads/1/git-commit', data={
        'commit_message': 'test: snapshot commit test',
        'do_push': 'false'
    }, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Ingestion Pipeline Refactor' in html

def test_generate_commit_message_endpoint(client, app):
    resp = client.get('/threads/1/generate-commit-message')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert 'commit_message' in data
    assert len(data['commit_message']) > 5


