import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from models import EpistemicNode, EpistemicEdge, Thread, Actor, utcnow

class EpistemicNodeType:
    CLAIM = "CLAIM"                 # Hypothesis, technical principle, architectural claim
    DECISION = "DECISION"           # Choice made at a Decision Gate
    EVIDENCE = "EVIDENCE"           # Benchmark, test result, telemetry trace, citation
    ARTIFACT = "ARTIFACT"           # File, code diff, PR, model checkpoint
    SOURCE = "SOURCE"               # User input, paper, spec, external link

class EpistemicEdgeType:
    SUPPORTS = "SUPPORTS"           # Evidence supports a Claim or Decision
    CONTRADICTS = "CONTRADICTS"     # Evidence/Claim refutes another Claim
    SUPERSEDES = "SUPERSEDES"       # New Decision/Claim replaces previous
    DERIVED_FROM = "DERIVED_FROM"   # Claim/Artifact originates from Source
    PRODUCED_BY = "PRODUCED_BY"     # Node produced by Actor/Agent


def record_epistemic_node(
    session: Session,
    thread_id: int,
    node_type: str,
    title: str,
    statement: str,
    confidence: float = 1.0,
    status: str = "ACTIVE",
    payload: Optional[Dict[str, Any]] = None,
    actor_id: Optional[int] = None
) -> EpistemicNode:
    """Creates a new knowledge or evidence node in the epistemic graph."""
    node = EpistemicNode(
        thread_id=thread_id,
        node_type=node_type.upper(),
        title=title.strip(),
        statement=statement.strip(),
        confidence=confidence,
        status=status.upper(),
        payload_json=json.dumps(payload) if payload else None,
        actor_id=actor_id
    )
    session.add(node)
    session.commit()
    return node


def link_epistemic_nodes(
    session: Session,
    source_node_id: int,
    target_node_id: int,
    edge_type: str,
    weight: float = 1.0,
    note: Optional[str] = None
) -> EpistemicEdge:
    """Creates a directed relationship edge between two epistemic nodes."""
    edge = EpistemicEdge(
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        edge_type=edge_type.upper(),
        weight=weight,
        note=note.strip() if note else None
    )
    session.add(edge)
    session.commit()
    return edge


def supersede_node(
    session: Session,
    old_node_id: int,
    new_node_id: int,
    reason: Optional[str] = None
) -> EpistemicEdge:
    """Marks an earlier claim or decision as SUPERSEDED and links the new node."""
    old_node = session.query(EpistemicNode).filter(EpistemicNode.id == old_node_id).first()
    if old_node:
        old_node.status = "SUPERSEDED"
    edge = link_epistemic_nodes(
        session,
        source_node_id=new_node_id,
        target_node_id=old_node_id,
        edge_type=EpistemicEdgeType.SUPERSEDES,
        note=reason
    )
    session.commit()
    return edge


def refute_node(
    session: Session,
    refuted_node_id: int,
    evidence_node_id: int,
    reason: Optional[str] = None
) -> EpistemicEdge:
    """Marks a claim as REFUTED and links the contradicting evidence."""
    target_node = session.query(EpistemicNode).filter(EpistemicNode.id == refuted_node_id).first()
    if target_node:
        target_node.status = "REFUTED"
    edge = link_epistemic_nodes(
        session,
        source_node_id=evidence_node_id,
        target_node_id=refuted_node_id,
        edge_type=EpistemicEdgeType.CONTRADICTS,
        note=reason
    )
    session.commit()
    return edge


def get_thread_epistemic_graph(session: Session, thread_id: int) -> Dict[str, Any]:
    """
    Returns the complete structured provenance graph for a thread:
    - active_claims: valid active technical claims
    - decisions: decisions and trade-off rationale
    - evidence: empirical verification and benchmarks
    - graph: node and edge topology for visualization
    """
    nodes = session.query(EpistemicNode).filter(EpistemicNode.thread_id == thread_id).all()
    node_ids = [n.id for n in nodes]

    edges = []
    if node_ids:
        edges = session.query(EpistemicEdge).filter(
            (EpistemicEdge.source_node_id.in_(node_ids)) |
            (EpistemicEdge.target_node_id.in_(node_ids))
        ).all()

    active_claims = [n.to_dict() for n in nodes if n.node_type == EpistemicNodeType.CLAIM and n.status == "ACTIVE"]
    decisions = [n.to_dict() for n in nodes if n.node_type == EpistemicNodeType.DECISION]
    evidence = [n.to_dict() for n in nodes if n.node_type == EpistemicNodeType.EVIDENCE]
    superseded = [n.to_dict() for n in nodes if n.status in ("SUPERSEDED", "REFUTED")]

    return {
        "thread_id": thread_id,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "active_claims": active_claims,
        "decisions": decisions,
        "evidence": evidence,
        "superseded": superseded,
        "nodes": [n.to_dict() for n in nodes],
        "edges": [e.to_dict() for e in edges]
    }


def trace_node_provenance(session: Session, node_id: int) -> Dict[str, Any]:
    """
    Traces the lineage of a node:
    - upstream: nodes that support, derive, or produced this node
    - downstream: nodes that depend on or were superseded by this node
    """
    node = session.query(EpistemicNode).filter(EpistemicNode.id == node_id).first()
    if not node:
        return {}

    incoming_edges = session.query(EpistemicEdge).filter(EpistemicEdge.target_node_id == node_id).all()
    outgoing_edges = session.query(EpistemicEdge).filter(EpistemicEdge.source_node_id == node_id).all()

    upstream = []
    for e in outgoing_edges:
        target = session.query(EpistemicNode).filter(EpistemicNode.id == e.target_node_id).first()
        if target:
            upstream.append({"relationship": e.edge_type, "node": target.to_dict(), "note": e.note})

    downstream = []
    for e in incoming_edges:
        source = session.query(EpistemicNode).filter(EpistemicNode.id == e.source_node_id).first()
        if source:
            downstream.append({"relationship": e.edge_type, "node": source.to_dict(), "note": e.note})

    return {
        "target_node": node.to_dict(),
        "upstream_lineage": upstream,
        "downstream_impact": downstream
    }


def format_epistemic_summary_markdown(session: Session, thread_id: int) -> str:
    """Generates a concise markdown briefing of the thread's epistemic claims and evidence."""
    graph = get_thread_epistemic_graph(session, thread_id)
    if graph["total_nodes"] == 0:
        return ""

    lines = ["\n## Provenance & Epistemic Lineage\n"]
    if graph["active_claims"]:
        lines.append("### Active Verified Claims")
        for c in graph["active_claims"]:
            lines.append(f"- **{c['title']}**: {c['statement']} (Confidence: {int(c['confidence']*100)}%)")

    if graph["decisions"]:
        lines.append("\n### Architectural Decisions & Rationale")
        for d in graph["decisions"]:
            lines.append(f"- **{d['title']}**: {d['statement']}")

    if graph["evidence"]:
        lines.append("\n### Supporting Empirical Evidence")
        for ev in graph["evidence"]:
            lines.append(f"- **{ev['title']}**: {ev['statement']}")

    if graph["superseded"]:
        lines.append("\n### Superseded / Refuted Hypotheses")
        for s in graph["superseded"]:
            lines.append(f"- ~~{s['title']}~~ [{s['status']}]: {s['statement']}")

    return "\n".join(lines)
