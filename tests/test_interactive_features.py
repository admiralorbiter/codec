import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from app import create_app
from config import Config
from seed import seed_database
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

def test_drawer_actions(client):
    # 1. Update frontier via endpoint
    resp_up = client.post('/threads/1/update', data={
        'frontier': 'Frontier updated via drawer.',
        'next_action': 'Proceed with next phase.'
    }, headers={'HX-Request': 'true'})
    assert resp_up.status_code == 200
    html = resp_up.data.decode('utf-8')
    assert 'Frontier updated via drawer.' in html
    assert 'Proceed with next phase.' in html

    # 2. Accept result
    resp_acc = client.post('/threads/1/accept', data={
        'note': 'Verified and accepted.'
    }, headers={'HX-Request': 'true'})
    assert resp_acc.status_code == 200

    # 3. Rework result
    resp_rew = client.post('/threads/1/rework', data={
        'feedback': 'Need better performance under load.'
    }, headers={'HX-Request': 'true'})
    assert resp_rew.status_code == 200
    assert 'Rework needed: Need better performance under load.' in resp_rew.data.decode('utf-8')

    # 4. Close thread
    resp_close = client.post('/threads/1/close', follow_redirects=True)
    assert resp_close.status_code == 200

def test_surface_crud(client):
    # Add surface to thread 2
    resp_add = client.post('/threads/2/surfaces', data={
        'surface_type': 'NOTEBOOK',
        'label': 'New Eval Notebook',
        'local_path': 'c:/Users/admir/Github/recurrence/new_eval.ipynb'
    }, follow_redirects=True)
    assert resp_add.status_code == 200
    html = resp_add.data.decode('utf-8')
    assert 'New Eval Notebook' in html

    # Delete surface
    resp_del = client.post('/surfaces/1/delete', data={'thread_id': 2}, follow_redirects=True)
    assert resp_del.status_code == 200

def test_universal_capture(client):
    # 1. Preview transcript
    transcript = 'Finished the first recurrence run. Persistence is observed. Started shuffled baseline compute now.'
    resp_prev = client.post('/capture/preview', json={'transcript': transcript})
    assert resp_prev.status_code == 200
    data = resp_prev.get_json()
    assert data['event_type'] in ('COMPUTE_STARTED', 'DISCOVERY', 'NOTE')
    assert 'Recurrence' in data['thread_name'] or 'Persistence' in data['thread_name']

    # 2. Commit capture
    resp_commit = client.post('/capture/commit', json={
        'thread_id': 2,
        'transcript': transcript,
        'proposed_state': 'RUNNING',
        'proposed_frontier': 'Persistence observed; baseline compute executing.',
        'proposed_next_action': 'Compare distributions once GPU finishes.'
    })
    assert resp_commit.status_code == 200
    res_data = resp_commit.get_json()
    assert res_data['status'] == 'ok'
    assert res_data['thread_id'] == 2

def test_friction_telemetry(client):
    resp = client.post('/friction', data={
        'note': 'Modal took two clicks to open on mobile view.',
        'category': 'FRICTION',
        'page_url': 'http://localhost:5050/'
    })
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'recorded'

def test_mcp_server(app):
    mcp = CodecMCPServer(db_uri=app.db_uri)
    
    # 1. List threads
    threads = mcp.list_threads()
    assert len(threads) >= 5

    # 2. Briefing
    briefing = mcp.get_thread_briefing(1)
    assert briefing['thread_id'] == 1
    assert 'frontier' in briefing

    # 3. Record update
    ev = mcp.record_update(1, 'MCP agent checkpoint: 24/24 tests passing.')
    assert ev['summary'] == 'MCP agent checkpoint: 24/24 tests passing.'

    # 4. Record blocker
    bl = mcp.record_blocker(1, 'Waiting for API token approval.', resume_condition='When token is issued')
    assert bl['status'] == 'blocked'

    # 5. Record result
    res = mcp.record_result(1, 'Agent finished ingestion migration.', updated_frontier='Migration ready for final review.')
    assert res['status'] == 'result_ready'

    # 6. Request review (Decision gate)
    dg = mcp.request_review(1, 'Select caching layer', options=[{'id': 'redis', 'title': 'Redis', 'recommended': True}])
    assert dg['status'] == 'decision_required'
