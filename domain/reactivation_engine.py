import os
import time
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from models import Thread, Event, Actor, utcnow
from domain.sse_service import broadcaster

class ConditionType(str, Enum):
    FILE_EXISTS = "FILE_EXISTS"
    AGENT_DONE = "AGENT_DONE"
    TIME_ELAPSED = "TIME_ELAPSED"
    GIT_CLEAN = "GIT_CLEAN"
    PROSE = "PROSE"

def parse_resume_condition(condition_str: Optional[str]) -> Dict[str, Any]:
    """
    Parses structured condition JSON or prefix-formatted string:
    - 'FILE_EXISTS: dist/app.js'
    - 'TIME_ELAPSED: 3600'
    - 'GIT_CLEAN: /path/to/repo'
    - 'AGENT_DONE'
    - JSON: '{"type": "FILE_EXISTS", "path": "..."}'
    """
    if not condition_str or not condition_str.strip():
        return {"type": ConditionType.PROSE, "spec": None, "raw": ""}

    text = condition_str.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            return {
                "type": data.get("type", ConditionType.PROSE),
                "spec": data.get("spec") or data.get("path") or data.get("target"),
                "raw": text
            }
        except Exception:
            pass

    for ctype in [ConditionType.FILE_EXISTS, ConditionType.AGENT_DONE, ConditionType.TIME_ELAPSED, ConditionType.GIT_CLEAN]:
        prefix = ctype.value
        if text.upper().startswith(f"{prefix}:") or text.upper().startswith(f"{prefix} "):
            spec = text[len(prefix) + 1:].strip()
            return {"type": ctype, "spec": spec, "raw": text}

    if text.upper() == ConditionType.AGENT_DONE.value:
        return {"type": ConditionType.AGENT_DONE, "spec": None, "raw": text}

    return {"type": ConditionType.PROSE, "spec": text, "raw": text}


def evaluate_thread_resume_condition(thread: Thread) -> Tuple[bool, str]:
    """
    Evaluates whether the thread's resume condition is satisfied in the real world.
    Returns (is_satisfied, reason).
    """
    cond = parse_resume_condition(thread.resume_condition)
    ctype = cond["type"]
    spec = cond["spec"]

    if ctype == ConditionType.FILE_EXISTS and spec:
        # Check if file exists relative to working tree or surface paths
        search_paths = [spec]
        ws = thread.get_working_set()
        if ws.get("repo_path"):
            search_paths.append(os.path.join(ws["repo_path"], spec))
        for s in getattr(thread, "surfaces", []):
            if s.local_path:
                search_paths.append(os.path.join(s.local_path, spec))

        for p in search_paths:
            if os.path.exists(p):
                return True, f"Observed file at '{p}'"
        return False, f"Waiting for file at '{spec}'"

    elif ctype == ConditionType.AGENT_DONE:
        # Check if active work packet is DELIVERED or ADOPTED
        wp = getattr(thread, "active_work_packet", None)
        if wp and wp.status in ("DELIVERED", "ADOPTED"):
            return True, f"Agent work packet result delivered: {wp.desired_outcome}"
        # Check if last event was an AGENT_RESULT
        if thread.events:
            last_event = thread.events[-1]
            if last_event.event_type in ("AGENT_RESULT", "RESULT_DELIVERED"):
                return True, f"Agent execution completed: {last_event.summary}"
        return False, "Waiting for agent completion"

    elif ctype == ConditionType.TIME_ELAPSED and spec:
        try:
            seconds_wait = float(spec)
            if thread.last_active_at:
                now = datetime.now(timezone.utc)
                last_act = thread.last_active_at if thread.last_active_at.tzinfo else thread.last_active_at.replace(tzinfo=timezone.utc)
                elapsed = (now - last_act).total_seconds()
                if elapsed >= seconds_wait:
                    return True, f"Timer elapsed ({int(elapsed)}s >= {int(seconds_wait)}s)"
                return False, f"Timer running ({int(elapsed)}s / {int(seconds_wait)}s)"
        except ValueError:
            return False, f"Invalid time spec '{spec}'"

    elif ctype == ConditionType.GIT_CLEAN:
        ws = thread.get_working_set()
        repo = ws.get("repo_path") or (thread.surfaces[0].local_path if thread.surfaces else None)
        if repo and os.path.exists(repo):
            try:
                import subprocess
                res = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, timeout=2)
                if res.returncode == 0 and not res.stdout.strip():
                    return True, f"Git repository at '{repo}' is clean"
            except Exception:
                pass
        return False, "Git repository has uncommitted changes"

    return False, "Manual resume condition requires human trigger"


def reactivate_thread(
    session: Session,
    thread_id: int,
    reason: str,
    target_state: str = "NEEDS_YOU"
) -> Optional[Thread]:
    """
    Transitions a thread from WAITING/PARKED to active state when its resume condition clears.
    Appends THREAD_REACTIVATED event to braid and publishes live SSE event.
    """
    thread = session.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        return None

    old_state = thread.state
    thread.state = target_state
    thread.is_living = True
    thread.frontier = f"Reactivated ({reason}). Ready for next move."
    thread.last_active_at = utcnow()

    # Find or create system actor
    system_actor = session.query(Actor).filter(Actor.name == "Reactivation Engine").first()
    if not system_actor:
        system_actor = Actor(name="Reactivation Engine", actor_type="SYSTEM")
        session.add(system_actor)
        session.flush()

    event = Event(
        thread_id=thread.id,
        actor_id=system_actor.id,
        event_type="THREAD_REACTIVATED",
        summary=f"⚡ Thread reactivated: {reason}",
        payload_json=json.dumps({
            "previous_state": old_state,
            "target_state": target_state,
            "condition_cleared": thread.resume_condition,
            "reason": reason,
            "reactivated_at": datetime.now(timezone.utc).isoformat()
        })
    )
    session.add(event)
    session.commit()

    # Broadcast live SSE update to cockpits
    broadcaster.broadcast(
        event_type="EVENT_APPENDED",
        thread_id=thread.id,
        payload={
            "id": event.id,
            "thread_id": thread.id,
            "event_type": event.event_type,
            "summary": event.summary,
            "occurred_at": event.occurred_at.strftime("%H:%M:%S") if event.occurred_at else "",
            "actor_name": system_actor.name
        }
    )
    broadcaster.broadcast(
        event_type="FRONTIER_UPDATED",
        thread_id=thread.id,
        payload={
            "thread_id": thread.id,
            "frontier": thread.frontier,
            "state": thread.state,
            "queue": thread.queue
        }
    )

    return thread


def check_all_waiting_conditions(session: Session) -> List[Dict[str, Any]]:
    """
    Scans all living threads waiting on external conditions and reactivates any satisfied threads.
    """
    waiting_threads = session.query(Thread).filter(
        Thread.is_living == True,
        Thread.state.in_(["WAITING", "BLOCKED", "PARKED"])
    ).all()

    reactivated = []
    for t in waiting_threads:
        if not t.resume_condition:
            continue
        is_satisfied, reason = evaluate_thread_resume_condition(t)
        if is_satisfied:
            reactivated_thread = reactivate_thread(session, t.id, reason)
            if reactivated_thread:
                reactivated.append({
                    "thread_id": t.id,
                    "thread_name": t.name,
                    "reason": reason,
                    "new_state": reactivated_thread.state
                })

    return reactivated
