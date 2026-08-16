import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models import Thread, Project, Actor, Event, Surface, utcnow
from domain.context_router import (
    compile_context_envelope,
    TargetProfile,
    TokenBudget,
    estimate_tokens
)

VALID_DOMAINS = ["All", "Professional", "Research", "Creative", "Personal"]
ATTENTION_MODES = ["ALL", "FOCUS", "INTERACTIVE", "SUPERVISE", "CONSUME"]

def get_current_focus_thread(db: Session) -> Optional[Thread]:
    """Retrieve the single active focus thread if set."""
    return db.query(Thread).filter(Thread.is_current_focus == True).first()

def get_living_threads(
    db: Session,
    domain: Optional[str] = None,
    project_id: Optional[int] = None,
    attention_mode: Optional[str] = None,
    search_query: Optional[str] = None,
    include_parked: bool = False
) -> List[Thread]:
    """Fetch living threads based on domain, project, attention mode, and search filters."""
    query = db.query(Thread).join(Thread.project, isouter=True)

    if not include_parked:
        query = query.filter(Thread.is_living == True, Thread.state != "DONE", Thread.state != "PARKED")
    else:
        query = query.filter(Thread.state != "DONE")

    if domain and domain.lower() != "all":
        query = query.filter(Project.domain.ilike(domain))

    if project_id:
        query = query.filter(Thread.project_id == project_id)

    if attention_mode and attention_mode.upper() == "CONSUME":
        query = query.filter(Thread.attention_fit == "CONSUME")


    if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        query = query.filter(
            or_(
                Thread.name.ilike(term),
                Thread.frontier.ilike(term),
                Thread.intent.ilike(term),
                Thread.next_action.ilike(term),
                Project.name.ilike(term)
            )
        )

    # Order by last active desc
    return query.order_by(Thread.last_active_at.desc(), Thread.updated_at.desc()).all()


def get_cockpit_queues(threads: List[Thread], mode: str = "ALL", attention_slice: Optional[str] = None) -> Dict[str, Any]:
    """Partition threads into cockpit attention queues with cognitive staging buffers."""
    from domain.attention_scheduler import filter_and_rank_by_attention
    
    sliced = filter_and_rank_by_attention(threads, mode=mode, attention_slice=attention_slice)
    active_threads = sliced["active_threads"]

    queues = {
        "NEEDS_YOU": [],
        "RUNNING": [],
        "READY": [],
        "WAITING": [],
    }
    for t in active_threads:
        q = t.queue
        if q in queues:
            queues[q].append(t)
        elif q == "ACTIVE":
            queues["READY"].append(t)
        else:
            queues["READY"].append(t)

    queues["staged_deep_work"] = sliced.get("staged_deep_work", [])
    queues["staged_count"] = sliced.get("staged_count", 0)
    return queues


from models import Thread, Project, Actor, Event, Surface, Relation


def get_all_projects(db: Session) -> List[Project]:
    return db.query(Project).filter(Project.status == "ACTIVE").order_by(Project.name).all()


def get_thread_by_id(db: Session, thread_id: int) -> Optional[Thread]:
    return db.query(Thread).filter(Thread.id == thread_id).first()


def get_thread_relations(db: Session, thread_id: int) -> List[Dict[str, Any]]:
    """Fetch incoming and outgoing semantic relations for a thread."""
    outgoing = db.query(Relation).filter(Relation.source_type == "thread", Relation.source_id == thread_id).all()
    incoming = db.query(Relation).filter(Relation.target_type == "thread", Relation.target_id == thread_id).all()
    
    results = []
    for r in outgoing:
        target_thread = db.query(Thread).filter(Thread.id == r.target_id).first()
        results.append({
            "id": r.id,
            "direction": "OUTGOING",
            "relation_type": r.relation_type,
            "other_thread_id": r.target_id,
            "other_thread_name": target_thread.name if target_thread else f"#{r.target_id}",
            "note": r.note
        })
    for r in incoming:
        source_thread = db.query(Thread).filter(Thread.id == r.source_id).first()
        results.append({
            "id": r.id,
            "direction": "INCOMING",
            "relation_type": r.relation_type,
            "other_thread_id": r.source_id,
            "other_thread_name": source_thread.name if source_thread else f"#{r.source_id}",
            "note": r.note
        })
    return results


def compile_ai_context_packet(thread: Thread) -> str:
    """
    Compiles a token-efficient, high-signal prompt packet formatted
    for immediate paste into ChatGPT, Claude, or an Antigravity agent.
    """
    ws = thread.get_working_set()
    
    lines = [
        f"### MISSION CONTEXT: [{thread.project.name if thread.project else 'General'}] {thread.name} (#{thread.id})",
        f"- **Primary Intent / Why this exists**: {thread.intent or 'Deliver thread objectives.'}",
        f"- **Current State / Queue**: {thread.state} ({thread.queue}) | Attention Fit: {thread.attention_fit or 'FOCUS'}",
        f"- **Current Frontier (Where work currently is)**: {thread.frontier or 'Frontier not articulated yet.'}",
    ]
    
    if thread.next_action:
        lines.append(f"- **Immediate First Move**: {thread.next_action}")
        
    if ws:
        ws_parts = []
        if ws.get("repo"):
            ws_parts.append(f"repo `{ws.get('repo')}`")
        if ws.get("branch"):
            ws_parts.append(f"branch `{ws.get('branch')}`")
        if ws.get("commit"):
            ws_parts.append(f"@{ws.get('commit')}")
        if ws.get("files_changed_count"):
            ws_parts.append(f"({ws.get('files_changed_count')} modified files, +{ws.get('additions', 0)}/-{ws.get('deletions', 0)})")
        if ws_parts:
            lines.append(f"- **Active Working Set**: {' '.join(ws_parts)}")
            
    if thread.surfaces:
        surf_str = ", ".join([f"[{s.surface_type}] {s.label}" + (f" ({s.uri})" if s.uri else "") for s in thread.surfaces[:4]])
        lines.append(f"- **Key Surfaces**: {surf_str}")
        
    decisions = [e for e in thread.events if "DECISION" in e.event_type]
    if decisions:
        last_d = decisions[-1]
        lines.append(f"- **Key Decision / Constraint**: {last_d.summary}")

    wp = getattr(thread, "active_work_packet", None)
    if wp:
        lines.append(f"\n### ACTIVE DELEGATION WORK PACKET (#{wp.id})")
        lines.append(f"- **Authority Level**: `{wp.authority_level}`")
        lines.append(f"- **Desired Outcome**: {wp.desired_outcome}")
        if wp.constraints:
            lines.append(f"- **Explicit Constraints**: {wp.constraints}")
        if wp.stop_conditions:
            lines.append(f"- **Stop Conditions (Yield control if met)**: {wp.stop_conditions}")
        if wp.expected_evidence:
            lines.append(f"- **Expected Evidence**: {wp.expected_evidence}")
        if wp.status == "REWORK_REQUESTED" and wp.result_evidence:
            lines.append(f"- **Rework Feedback / Fix Required**: {wp.result_summary}")

    lines.append("\n**TASK INSTRUCTION**: Proceed from the current frontier above. Preserve architectural constraints and state your findings and recommended next move clearly.")
    return "\n".join(lines)


def generate_smart_commit_message(thread: Thread) -> str:
    """
    Generates an accurate Conventional Commit message strictly derived from
    the actual Git working tree status, modified files, and diff changes.
    """
    import subprocess
    from pathlib import Path

    # 1. Locate repository path
    repo_path = None
    ws = thread.get_working_set()
    if ws.get("repo_path") and os.path.exists(ws.get("repo_path")):
        repo_path = ws.get("repo_path")
    else:
        for s in thread.surfaces:
            if s.local_path and os.path.exists(s.local_path):
                repo_path = s.local_path
                break
    if not repo_path and os.path.exists(".git"):
        repo_path = os.getcwd()

    # 2. Inspect real Git working tree status
    file_statuses = []  # List of tuples: (status_code, filepath)
    if repo_path and os.path.exists(repo_path):
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().splitlines():
                    status_part = line[:2].strip()
                    file_part = line[2:].strip()
                    if file_part:
                        file_statuses.append((status_part or "M", file_part))
        except Exception:
            pass

    if not file_statuses:
        return f"chore({thread.name.lower()}): working tree clean (no staged or unstaged changes)"

    changed_files = [f for _, f in file_statuses]
    changed_str = " ".join(changed_files).lower()

    # 3. Derive commit type and primary scope strictly from changed files
    ctype = "feat"
    scope = "core"
    summary_parts = []

    # Detect dominant feature / subsystem from files
    if "attention_scheduler" in changed_str or "horizon5" in changed_str or "attention" in changed_str:
        scope = "attention"
        summary_parts.append("implement Horizon 5 attention-aware execution & cognitive scheduler")
    elif "context_router" in changed_str or "router" in changed_str:
        scope = "router"
        summary_parts.append("implement provider-neutral context router & target prompt compilers")
    elif "work_packet" in changed_str:
        scope = "work-packets"
        summary_parts.append("update work packet dispatch and adoption lifecycle")
    elif "sse" in changed_str or "stream" in changed_str:
        scope = "stream"
        summary_parts.append("enhance real-time event streaming and telemetry")
    elif "mcp" in changed_str:
        scope = "mcp"
        summary_parts.append("update autonomous agent MCP server tooling")
    elif all("test" in f.lower() for f in changed_files):
        ctype = "test"
        scope = "tests"
        summary_parts.append(f"add and update test suite ({len(changed_files)} test files)")
    elif all("doc" in f.lower() or f.endswith(".md") for f in changed_files):
        ctype = "docs"
        scope = "docs"
        summary_parts.append("update technical documentation and specifications")
    elif all("static" in f or "template" in f for f in changed_files):
        scope = "ui"
        summary_parts.append("update tactical cockpit interface and templates")
    elif "models.py" in changed_str or "migration" in changed_str:
        scope = "models"
        summary_parts.append("update database models and schema")
    else:
        scope = (thread.project.name if thread.project else "core").lower().replace(" ", "-")
        summary_parts.append(f"update {len(changed_files)} files across {scope}")

    summary = summary_parts[0]
    header = f"{ctype}({scope}): {summary}"

    # 4. Generate structured bullets directly from each changed file
    bullets = []
    for code, fpath in file_statuses:
        p = Path(fpath)
        fname = p.name
        is_new = code in ("??", "A")
        is_del = code == "D"
        tag = "[NEW]" if is_new else ("[DEL]" if is_del else "[MOD]")

        desc = ""
        if "test" in fname:
            desc = "automated unit and integration test suite"
        elif "context_router.py" in fname:
            desc = "target prompt profiles (Antigravity, ChatGPT, Claude, Local Agent, Audio)"
        elif "attention_scheduler.py" in fname:
            desc = "Horizon 5 cognitive load & attention scheduler"
        elif "reactivation_engine.py" in fname:
            desc = "Horizon 6 conditional reactivation & prospective memory"
        elif "epistemic_graph.py" in fname:
            desc = "Horizon 7 provenance & epistemic graph engine"
        elif "personal_os_scheduler.py" in fname:
            desc = "Horizon 8 personal OS scheduler & throughput telemetry"
        elif "_context_router_modal.html" in fname:
            desc = "interactive Context Router modal with live preview & token budget"
        elif "seed_dogfood.py" in fname:
            desc = "clean database initialization for real active projects"
        elif "mcp_server.py" in fname:
            desc = "expose compile_context_envelope tool via MCP stdio protocol"
        elif "models.py" in fname:
            desc = "database models and telemetry properties"
        elif "transitions.py" in fname:
            desc = "lifecycle state transitions and event dispatch"
        elif "migrations.py" in fname:
            desc = "database schema version migrations"
        elif "app.py" in fname:
            desc = "HTTP endpoints and context router routes"
        elif "codec.css" in fname:
            desc = "tactical UI styles and modal layout"
        elif "codec.js" in fname:
            desc = "client-side modal controller and live fetch"
        elif "thread_workspace.html" in fname:
            desc = "workspace layout and toolbar integration"
        elif "_thread_drawer.html" in fname:
            desc = "drawer quick actions and context button"
        elif "base.html" in fname:
            desc = "global navigation and modal container"
        else:
            desc = f"{p.parent.as_posix() if str(p.parent) != '.' else 'root'}"

        bullets.append(f"- {tag} `{fpath}` ({desc})")

    if bullets:
        header += "\n\n" + "\n".join(bullets[:15])

    return header


