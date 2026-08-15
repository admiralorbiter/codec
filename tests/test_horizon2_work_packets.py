import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from app import create_app
from config import Config
from seed import seed_database
from domain.transitions import (
    create_work_packet,
    dispatch_work_packet,
    deliver_work_packet_result,
    adopt_work_packet_result,
    request_work_packet_rework
)
from domain.queries import compile_ai_context_packet, get_thread_by_id
from models import Thread, WorkPacket
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

def test_work_packet_lifecycle_domain(app):
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(app.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Create work packet
    wp = create_work_packet(
        session,
        thread_id=1,
        desired_outcome='Implement Horizon 2 Work Packet Engine',
        constraints='Do not modify config.py',
        stop_conditions='Stop if test failure > 1',
        authority_level='EXECUTE_AND_TEST',
        expected_evidence='Passing pytest suite (40+ tests)'
    )
    assert wp.id is not None
    assert wp.status == 'PREPARED'
    thread = session.query(Thread).filter(Thread.id == 1).first()
    assert thread.queue == 'READY'
    assert 'Work Packet Prepared' in thread.frontier

    # 2. Dispatch work packet
    wp = dispatch_work_packet(session, wp.id, actor_name='Antigravity')
    assert wp.status == 'DISPATCHED'
    session.refresh(thread)
    assert thread.queue == 'RUNNING'
    assert 'Agent executing' in thread.frontier

    # 3. Deliver result
    wp = deliver_work_packet_result(
        session,
        wp.id,
        result_summary='Completed Work Packet model and transitions',
        evidence='pytest tests/test_horizon2_work_packets.py (all green)'
    )
    assert wp.status == 'DELIVERED'
    session.refresh(thread)
    assert thread.queue == 'NEEDS_YOU'
    assert 'Result Delivered' in thread.frontier

    # 4. Request rework
    wp = request_work_packet_rework(
        session,
        wp.id,
        rework_feedback='Please add stop-condition preset helper buttons.'
    )
    assert wp.status == 'REWORK_REQUESTED'
    session.refresh(thread)
    assert thread.queue == 'READY'
    assert 'Rework Requested' in thread.frontier

    # 5. Adopt result
    wp = adopt_work_packet_result(session, wp.id)
    assert wp.status == 'ACCEPTED'
    session.refresh(thread)
    assert thread.queue == 'READY'
    assert 'Adopted result' in thread.frontier

    session.close()

def test_work_packet_context_packet_injection(app):
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(app.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    create_work_packet(
        session,
        thread_id=1,
        desired_outcome='Optimize SQLite Query Plan',
        constraints='Preserve transaction safety',
        stop_conditions='Stop if memory consumption > 100MB',
        authority_level='EXECUTE_AND_TEST'
    )
    thread = get_thread_by_id(session, 1)
    packet_md = compile_ai_context_packet(thread)

    assert 'ACTIVE DELEGATION WORK PACKET' in packet_md
    assert 'Optimize SQLite Query Plan' in packet_md
    assert 'Stop if memory consumption > 100MB' in packet_md
    assert 'Preserve transaction safety' in packet_md

    session.close()

def test_work_packet_http_routes(client, app):
    # 1. Create via HTTP
    resp = client.post('/threads/1/work-packets', data={
        'desired_outcome': 'Build Webhook Event Trigger',
        'constraints': 'No external dependencies',
        'stop_conditions': 'Stop if endpoint fails',
        'authority_level': 'EXECUTE_AND_TEST',
        'auto_dispatch': 'false'
    }, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'DELEGATED WORK PACKET' in html
    assert 'Build Webhook Event Trigger' in html

    # 2. Query active via API
    resp_api = client.get('/threads/1/work-packet/active')
    assert resp_api.status_code == 200
    data = resp_api.get_json()
    assert data['status'] == 'active'
    wp_id = data['work_packet']['id']

    # 3. Dispatch via HTTP
    resp_disp = client.post(f'/work-packets/{wp_id}/dispatch', data={'actor_name': 'Antigravity'}, follow_redirects=True)
    assert resp_disp.status_code == 200

    # 4. Deliver via JSON API
    resp_deliv = client.post(f'/work-packets/{wp_id}/deliver', json={
        'result_summary': 'Webhook trigger operational',
        'evidence': 'Delivered 5/5 test events successfully.'
    })
    assert resp_deliv.status_code == 200
    deliv_data = resp_deliv.get_json()
    assert deliv_data['status'] == 'delivered'

    # 5. Adopt via HTTP
    resp_adopt = client.post(f'/work-packets/{wp_id}/adopt', follow_redirects=True)
    assert resp_adopt.status_code == 200

def test_mcp_server_work_packet_integration(app):
    server = CodecMCPServer(db_uri=app.db_uri)

    # 1. Create packet in DB
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(app.db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    wp = create_work_packet(
        session,
        thread_id=1,
        desired_outcome='MCP Autonomous Work Packet Test'
    )
    wp_id = wp.id
    session.close()

    # 2. MCP read active packet
    res = server.get_active_work_packet(1)
    assert res['status'] == 'ok'
    assert res['work_packet']['id'] == wp_id
    assert res['work_packet']['desired_outcome'] == 'MCP Autonomous Work Packet Test'

    # 3. MCP deliver result
    res_deliv = server.deliver_work_packet(
        thread_id=1,
        work_packet_id=wp_id,
        result_summary='MCP Agent finished execution cleanly',
        evidence='All 40 tests passed'
    )
    assert res_deliv['status'] == 'delivered'
    assert res_deliv['work_packet']['status'] == 'DELIVERED'
