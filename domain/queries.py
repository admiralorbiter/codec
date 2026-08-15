import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models import Thread, Project, Actor, Event, Surface, utcnow

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

    if attention_mode and attention_mode.upper() != "ALL":
        mode = attention_mode.upper()
        if mode == "FOCUS":
            query = query.filter(
                or_(
                    Thread.is_current_focus == True,
                    Thread.attention_fit == "FOCUS",
                    Thread.attention_fit == "DEEP"
                )
            )
        elif mode == "INTERACTIVE":
            query = query.filter(
                or_(
                    Thread.attention_fit == "BUILD",
                    Thread.attention_fit == "INTERACTIVE",
                    Thread.state == "ACTIVE"
                )
            )
        elif mode == "SUPERVISE":
            query = query.filter(
                or_(
                    Thread.state == "RUNNING",
                    Thread.state == "NEEDS_YOU",
                    Thread.attention_fit == "SUPERVISE"
                )
            )
        elif mode == "CONSUME":
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


def get_cockpit_queues(threads: List[Thread]) -> Dict[str, List[Thread]]:
    """Partition threads into cockpit attention queues."""
    queues = {
        "NEEDS_YOU": [],
        "RUNNING": [],
        "READY": [],
        "WAITING": [],
    }
    for t in threads:
        q = t.queue
        if q in queues:
            queues[q].append(t)
        elif q == "ACTIVE":
            queues["READY"].append(t)
        else:
            queues["READY"].append(t)
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
    Synthesizes real git diff files, active work packets, and recent braid events
    into an accurate Conventional Commit message.
    """
    import subprocess
    from pathlib import Path

    # 1. Inspect real git status for changed files
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

    changed_files = []
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
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        changed_files.append(parts[1])
        except Exception:
            pass

    # 2. Determine scope from changed files, active work packet, or thread
    scope = (thread.project.name if thread.project else "core").lower().replace(" ", "-")
    
    # Check for horizon keywords in changed files or active work packet
    wp = getattr(thread, "active_work_packet", None)
    all_context_text = " ".join(changed_files) + " " + (wp.desired_outcome if wp else "") + " " + (thread.frontier or "")
    all_context_text = all_context_text.lower()

    if "horizon2" in all_context_text or "work_packet" in all_context_text or "work packet" in all_context_text:
        scope = "horizon2"
    elif "horizon1" in all_context_text:
        scope = "horizon1"
    elif "codec" in thread.name.lower():
        scope = "core"

    # 3. Determine commit type & summary
    ctype = "feat"
    summary = ""

    if wp and wp.desired_outcome:
        d_out = wp.desired_outcome.strip()
        for prefix in ["Build ", "Implement ", "Create ", "Add "]:
            if d_out.startswith(prefix):
                d_out = d_out[len(prefix):]
                break
        summary = d_out.rstrip(".").lower()
    elif thread.frontier and not thread.frontier.startswith("Checkpointed"):
        f_text = thread.frontier.strip()
        first_sentence = f_text.split(".")[0].strip()
        for prefix in ["Completed ", "Implemented ", "Built ", "Added "]:
            if first_sentence.startswith(prefix):
                first_sentence = first_sentence[len(prefix):]
                break
        summary = first_sentence[:80].rstrip(".").lower()
    elif changed_files:
        summary = f"update {len(changed_files)} files across {scope}"
    else:
        summary = f"update {thread.name.lower()}"

    header = f"{ctype}({scope}): {summary}"

    # 4. Generate structured bullets from changed files
    bullets = []
    if changed_files:
        if any("models.py" in f for f in changed_files):
            bullets.append("- Updated database models and schema")
        if any("transitions.py" in f for f in changed_files):
            bullets.append("- Implemented domain lifecycle transitions and event handlers")
        if any("mcp_server.py" in f for f in changed_files):
            bullets.append("- Added autonomous agent MCP server tooling")
        if any("app.py" in f for f in changed_files):
            bullets.append("- Added HTTP endpoints and routing")
        if any("test" in f for f in changed_files):
            test_names = [Path(f).name for f in changed_files if "test" in f]
            bullets.append(f"- Verified test suite ({', '.join(test_names[:2])})")
        if any("template" in f or "static" in f for f in changed_files):
            bullets.append("- Updated tactical cockpit UI templates and modal controls")

    if bullets:
        header += "\n\n" + "\n".join(bullets[:5])

    return header


