import pytest
import os
import tempfile
from sqlalchemy import create_engine
from app import create_app
from config import Config

@pytest.fixture
def empty_app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'

    app = create_app(TestConfig)
    
    yield app
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

@pytest.fixture
def client(empty_app):
    return empty_app.test_client()

def test_cockpit_empty_state(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'CODEC' in html
    assert 'ACTIVE COGNITIVE RADAR // 0 THREADS' in html
    assert 'No threads require immediate human decision.' in html

def test_queues_partial_empty_state(client):
    response = client.get('/queues')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'No threads require immediate human decision.' in html

def test_living_threads_empty_state(client):
    response = client.get('/living')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'MISSION CONTROL' in html
    assert 'No living threads in current view.' in html

def test_parallel_cockpit_empty_state(client):
    response = client.get('/parallel')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'PARALLEL CODEC COMMS MATRIX' in html
    assert 'CH 1 // 140.85' in html
    assert 'COMMS CHANNEL 1 STANDBY' in html
    assert 'NO LIVING THREADS ACTIVE' in html

def test_parallel_cockpit_column_variants_empty_state(client):
    resp_2 = client.get('/parallel?cols=2')
    assert resp_2.status_code == 200
    html_2 = resp_2.data.decode('utf-8')
    assert 'grid-cols-2' in html_2
    assert 'COMMS CHANNEL 2 STANDBY' in html_2

    resp_4 = client.get('/parallel?cols=4')
    assert resp_4.status_code == 200
    html_4 = resp_4.data.decode('utf-8')
    assert 'grid-cols-4' in html_4
    assert 'COMMS CHANNEL 4 STANDBY' in html_4

def test_api_threads_empty_state(client):
    response = client.get('/api/threads')
    assert response.status_code == 200
    data = response.get_json()
    assert data == []

def test_create_thread_on_empty_db(client):
    response = client.post('/threads', data={
        'name': 'Cold Start Investigation',
        'intent': 'Verify thread creation on empty database.'
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Cold Start Investigation' in html
    assert 'CURRENT FOCUS' in html
