import pytest
import os
import tempfile
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import create_app
from config import Config
from models import Base, Thread, Project, Actor, EpistemicNode, EpistemicEdge
from domain.epistemic_graph import (
    EpistemicNodeType,
    EpistemicEdgeType,
    record_epistemic_node,
    link_epistemic_nodes,
    supersede_node,
    refute_node,
    get_thread_epistemic_graph,
    trace_node_provenance,
    format_epistemic_summary_markdown
)
from domain.context_router import compile_context_envelope

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


def test_epistemic_graph_crud_and_lineage(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="KnowledgeGraph", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    t = Thread(
        project_id=proj.id,
        name="Epistemic Provenance Engine",
        intent="Trace claim origins",
        frontier="Graph initialized",
        state="ACTIVE",
        is_living=True
    )
    session.add(t)
    session.commit()

    # 1. Record Source
    source = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.SOURCE,
        title="NASA-STD-3001 Specification",
        statement="Complex cockpit interfaces must use unequal semantic salience for operator state."
    )

    # 2. Record Claim derived from Source
    claim = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.CLAIM,
        title="Unequal Salience Principle",
        statement="Frontier and next moves must be perceptually distinct from chronological logs.",
        confidence=0.95
    )
    link_epistemic_nodes(session, source_node_id=claim.id, target_node_id=source.id, edge_type=EpistemicEdgeType.DERIVED_FROM)

    # 3. Record Empirical Evidence supporting Claim
    evidence = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.EVIDENCE,
        title="Usability Time-to-Orient Benchmark",
        statement="Situation strip reduced operator orientation latency from 18s to 2.4s."
    )
    link_epistemic_nodes(session, source_node_id=evidence.id, target_node_id=claim.id, edge_type=EpistemicEdgeType.SUPPORTS)

    # Verify Graph
    graph = get_thread_epistemic_graph(session, t.id)
    assert graph["total_nodes"] == 3
    assert graph["total_edges"] == 2
    assert len(graph["active_claims"]) == 1
    assert graph["active_claims"][0]["title"] == "Unequal Salience Principle"

    # Trace provenance of claim
    trace = trace_node_provenance(session, claim.id)
    assert trace["target_node"]["title"] == "Unequal Salience Principle"
    assert len(trace["upstream_lineage"]) == 1
    assert trace["upstream_lineage"][0]["node"]["title"] == "NASA-STD-3001 Specification"
    assert len(trace["downstream_impact"]) == 1
    assert trace["downstream_impact"][0]["node"]["title"] == "Usability Time-to-Orient Benchmark"

    # Markdown Summary
    md = format_epistemic_summary_markdown(session, t.id)
    assert "Active Verified Claims" in md
    assert "Unequal Salience Principle" in md
    assert "Supporting Empirical Evidence" in md

    session.close()


def test_supersede_and_refute_lifecycle(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="HypothesisLab", domain="Research", status="ACTIVE")
    session.add(proj)
    session.flush()

    t = Thread(project_id=proj.id, name="Cache Architecture", state="ACTIVE", is_living=True)
    session.add(t)
    session.commit()

    # Hypothesis 1: Redis
    h1 = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.CLAIM,
        title="Redis Central Cache",
        statement="Use external Redis server for all thread session states."
    )

    # Hypothesis 2: In-Memory SQLite (Supersedes H1)
    h2 = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.CLAIM,
        title="Local In-Memory SQLite Cache",
        statement="Use SQLite WAL mode locally with zero external network overhead."
    )
    supersede_node(session, old_node_id=h1.id, new_node_id=h2.id, reason="Eliminates external docker dependency")

    session.refresh(h1)
    session.refresh(h2)
    assert h1.status == "SUPERSEDED"
    assert h2.status == "ACTIVE"

    # Refute a claim with contradicting benchmark
    bad_claim = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.CLAIM,
        title="JSON File Storage is Fastest",
        statement="Plain JSON files have lower latency than SQLite."
    )
    bench_evidence = record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.EVIDENCE,
        title="SQLite vs JSON Benchmark",
        statement="SQLite is 8.4x faster for indexed thread lookups under concurrency."
    )
    refute_node(session, refuted_node_id=bad_claim.id, evidence_node_id=bench_evidence.id, reason="Benchmark disproved claim")

    session.refresh(bad_claim)
    assert bad_claim.status == "REFUTED"

    session.close()


def test_context_router_includes_epistemic_claims(app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="EpistemicRouter", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    t = Thread(
        project_id=proj.id,
        name="Router Provenance Test",
        frontier="Testing context router epistemic injection",
        state="ACTIVE",
        is_living=True
    )
    session.add(t)
    session.commit()

    record_epistemic_node(
        session=session,
        thread_id=t.id,
        node_type=EpistemicNodeType.CLAIM,
        title="Zero-Lag Context Ingestion",
        statement="Context routers must compile in <10ms to avoid UI blocking."
    )

    envelope = compile_context_envelope(t, target="ANTIGRAVITY", budget="STANDARD")
    assert "Zero-Lag Context Ingestion" in envelope["content"]
    assert "Provenance & Verified Claims" in envelope["content"]

    session.close()


def test_http_epistemic_endpoints(client, app_and_db):
    _, _, engine = app_and_db
    Session = sessionmaker(bind=engine)
    session = Session()

    proj = Project(name="HTTPEpistemic", domain="Core", status="ACTIVE")
    session.add(proj)
    session.flush()

    t = Thread(project_id=proj.id, name="HTTP Epistemic Thread", state="ACTIVE", is_living=True)
    session.add(t)
    session.commit()
    t_id = t.id
    session.close()

    # 1. Create Node 1
    resp1 = client.post(f"/threads/{t_id}/epistemic/nodes", json={
        "node_type": "CLAIM",
        "title": "Decoupled Git Generator",
        "statement": "Commit messages must be derived 100% from working tree diffs."
    })
    assert resp1.status_code == 200
    n1_id = resp1.get_json()["node"]["id"]

    # 2. Create Node 2
    resp2 = client.post(f"/threads/{t_id}/epistemic/nodes", json={
        "node_type": "EVIDENCE",
        "title": "Git Diff Consistency Test",
        "statement": "66/66 unit tests verify 100% accurate file mapping."
    })
    assert resp2.status_code == 200
    n2_id = resp2.get_json()["node"]["id"]

    # 3. Link Nodes
    resp_link = client.post(f"/threads/{t_id}/epistemic/links", json={
        "source_node_id": n2_id,
        "target_node_id": n1_id,
        "edge_type": "SUPPORTS",
        "note": "Validated in CI"
    })
    assert resp_link.status_code == 200
    assert resp_link.get_json()["edge"]["edge_type"] == "SUPPORTS"

    # 4. Fetch Lineage
    resp_lineage = client.get(f"/threads/{t_id}/epistemic/lineage")
    assert resp_lineage.status_code == 200
    data = resp_lineage.get_json()
    assert data["graph"]["total_nodes"] == 2
    assert data["graph"]["total_edges"] == 1
    assert "Decoupled Git Generator" in data["summary_markdown"]
