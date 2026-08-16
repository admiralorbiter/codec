import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from config import Config
from models import Base, Thread, Project, Actor, Event, WorkPacket, Relation
from domain.context_router import (
    compile_context_envelope,
    TargetProfile,
    TokenBudget,
    estimate_tokens
)
from domain.queries import get_thread_by_id, get_thread_relations
from mcp_server import CodecMCPServer

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

@pytest.fixture
def seed_test_thread(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="ContextEngine", domain="Research", status="ACTIVE")
    session.add(proj)
    session.flush()

    actor = Actor(name="Antigravity", actor_type="AGENT")
    session.add(actor)
    session.flush()

    t1 = Thread(
        project_id=proj.id,
        name="Context Router Engine",
        intent="Compile minimal prompt envelopes for fresh agents.",
        frontier="Horizon 4 implementation in progress.",
        state="RUNNING",
        attention_fit="SUPERVISE",
        current_actor_id=actor.id,
        next_action="Run test suite and verify envelope sizes.",
        working_set_json=json.dumps({
            "repo": "codec",
            "branch": "feat/h4-router",
            "files_changed_count": 3,
            "additions": 140,
            "deletions": 12,
            "tests_status": "54/54 passing"
        }),
        is_living=True,
        is_current_focus=True
    )
    session.add(t1)
    session.flush()

    wp = WorkPacket(
        thread_id=t1.id,
        desired_outcome="Implement multi-resolution target prompt compilers.",
        constraints="Preserve WCAG 2.2 contrast and NASA display principles.",
        stop_conditions="Stop if prompt envelope exceeds 2000 tokens.",
        expected_evidence="Passing pytest suite",
        status="DISPATCHED"
    )
    session.add(wp)
    session.flush()

    # Create related thread
    t2 = Thread(
        project_id=proj.id,
        name="Audio Stream Synthesis",
        intent="Generate synthesized audio briefs.",
        frontier="Listening episodes active.",
        state="READY",
        is_living=True
    )
    session.add(t2)
    session.flush()

    rel = Relation(
        source_type="THREAD",
        source_id=t1.id,
        target_type="THREAD",
        target_id=t2.id,
        relation_type="DEPENDS_ON",
        note="Audio digest output depends on synthesis parameters."
    )
    session.add(rel)
    session.commit()

    thread_id = t1.id
    session.close()
    return thread_id


def test_target_profiles_generate_distinct_envelopes(app_and_db, seed_test_thread):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    thread = get_thread_by_id(session, seed_test_thread)
    relations = get_thread_relations(session, seed_test_thread)

    # 1. Antigravity profile
    ag = compile_context_envelope(thread, target="ANTIGRAVITY", budget="STANDARD", relations=relations)
    assert ag["target"] == "ANTIGRAVITY"
    assert "AGENT TASK DIRECTIVE" in ag["content"]
    assert "feat/h4-router" in ag["content"]
    assert "STOP CONDITIONS" in ag["content"]
    assert ag["token_estimate"] > 50

    # 2. ChatGPT profile
    gpt = compile_context_envelope(thread, target="CHATGPT", budget="STANDARD", relations=relations)
    assert gpt["target"] == "CHATGPT"
    assert "You are collaborating on project" in gpt["content"]
    assert "Where Work Currently Left Off" in gpt["content"]

    # 3. Claude profile
    claude = compile_context_envelope(thread, target="CLAUDE", budget="STANDARD", relations=relations)
    assert claude["target"] == "CLAUDE"
    assert "<frontier>" in claude["content"]
    assert "<work_packet>" in claude["content"]

    # 4. Local Agent profile (Ultra compact)
    local = compile_context_envelope(thread, target="LOCAL_AGENT", budget="COMPACT", relations=relations)
    assert local["target"] == "LOCAL_AGENT"
    assert "FRONTIER:" in local["content"]
    assert local["token_estimate"] < ag["token_estimate"]

    # 5. Audio Digest profile
    audio = compile_context_envelope(thread, target="AUDIO_DIGEST", budget="STANDARD", relations=relations)
    assert audio["target"] == "AUDIO_DIGEST"
    assert "Here is your audio brief" in audio["content"]

    session.close()


def test_token_budget_scaling(app_and_db, seed_test_thread):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    thread = get_thread_by_id(session, seed_test_thread)
    relations = get_thread_relations(session, seed_test_thread)

    compact = compile_context_envelope(thread, target="ANTIGRAVITY", budget="COMPACT", relations=relations)
    standard = compile_context_envelope(thread, target="ANTIGRAVITY", budget="STANDARD", relations=relations)

    assert compact["token_estimate"] <= standard["token_estimate"]
    session.close()


def test_http_context_router_compile_endpoint(client, seed_test_thread):
    # GET request
    resp = client.get(f"/threads/{seed_test_thread}/context-router/compile?target=CHATGPT&budget=STANDARD")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["target"] == "CHATGPT"
    assert "Context Router Engine" in data["content"]

    # POST request with JSON
    resp_post = client.post(f"/threads/{seed_test_thread}/context-router/compile", json={
        "target": "AUDIO_DIGEST",
        "budget": "COMPACT"
    })
    assert resp_post.status_code == 200
    data_post = resp_post.get_json()
    assert data_post["target"] == "AUDIO_DIGEST"
    assert "audio brief" in data_post["content"]


def test_mcp_compile_context_envelope(app_and_db, seed_test_thread):
    _, db_uri, _ = app_and_db
    server = CodecMCPServer(db_uri=db_uri)
    envelope = server.compile_context(thread_id=seed_test_thread, target="CLAUDE", budget="STANDARD")
    assert envelope["target"] == "CLAUDE"
    assert "<frontier>" in envelope["content"]
