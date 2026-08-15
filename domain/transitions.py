import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Thread, Event, Episode, Actor, Surface, FrictionLog, utcnow

def set_current_focus(db: Session, thread_id: int) -> Thread:
    """Set a single thread as the active cognitive focus."""
    # Reset any existing current focus
    db.query(Thread).filter(Thread.is_current_focus == True).update({"is_current_focus": False})

    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    thread.is_current_focus = True
    thread.last_active_at = utcnow()
    if thread.state == "PARKED":
        thread.state = "ACTIVE"
        thread.is_living = True

    event = Event(
        thread_id=thread.id,
        event_type="FOCUS_ACQUIRED",
        summary="Set as active cognitive focus.",
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def park_thread(
    db: Session,
    thread_id: int,
    note: Optional[str] = None,
    resume_condition: Optional[str] = None
) -> Thread:
    """Park a thread cleanly, capturing stopping state."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    thread.state = "PARKED"
    thread.is_current_focus = False
    if resume_condition and resume_condition.strip():
        thread.resume_condition = resume_condition.strip()

    # Close any open episode
    open_episodes = db.query(Episode).filter(Episode.thread_id == thread.id, Episode.ended_at == None).all()
    for ep in open_episodes:
        ep.ended_at = utcnow()
        ep.ending_reason = note or "Parked by user."

    payload = {
        "stopping_frontier": thread.frontier,
        "resume_condition": thread.resume_condition,
        "note": note
    }

    event = Event(
        thread_id=thread.id,
        event_type="PARKED",
        summary=note or "Parked thread cleanly to suspend working memory.",
        payload_json=json.dumps(payload),
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def resume_thread(db: Session, thread_id: int) -> Thread:
    """Resume a thread and acquire focus."""
    # Reset existing focus
    db.query(Thread).filter(Thread.is_current_focus == True).update({"is_current_focus": False})

    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    thread.state = "ACTIVE"
    thread.is_living = True
    thread.is_current_focus = True
    thread.last_active_at = utcnow()

    # Start new episode
    episode = Episode(
        thread_id=thread.id,
        started_at=utcnow(),
        mode=thread.attention_fit or "FOCUS",
        summary="Resumed work session."
    )
    db.add(episode)
    db.flush()

    event = Event(
        thread_id=thread.id,
        episode_id=episode.id,
        event_type="RESUMED",
        summary="Resumed thread and started new work episode.",
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def make_decision(
    db: Session,
    thread_id: int,
    choice: str,
    reasoning: Optional[str] = None
) -> Thread:
    """Resolve a decision gate on a thread."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    payload = {
        "chosen_option": choice,
        "reasoning": reasoning or "Selected via decision gate."
    }

    event = Event(
        thread_id=thread.id,
        event_type="DECISION",
        summary=f"Decision made: {choice}",
        payload_json=json.dumps(payload),
        occurred_at=utcnow()
    )
    db.add(event)

    # Update frontier and state
    thread.frontier = f"Architecture chosen: {choice}. Proceeding with implementation."
    thread.next_action = f"Run migration handlers using {choice} approach."
    thread.state = "ACTIVE"
    thread.last_active_at = utcnow()

    db.commit()
    db.refresh(thread)
    return thread


def append_event(
    db: Session,
    thread_id: int,
    event_type: str,
    summary: str,
    payload_dict: Optional[Dict[str, Any]] = None,
    actor_id: Optional[int] = None
) -> Event:
    """Record an immutable semantic work transition."""
    event = Event(
        thread_id=thread_id,
        event_type=event_type,
        summary=summary,
        payload_json=json.dumps(payload_dict) if payload_dict else None,
        actor_id=actor_id,
        occurred_at=utcnow()
    )
    db.add(event)
    
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if thread:
        thread.last_active_at = utcnow()

    db.commit()
    db.refresh(event)
    return event


def close_thread(db: Session, thread_id: int, note: Optional[str] = None) -> Thread:
    """Mark thread as DONE, removing from living radar."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    thread.state = "DONE"
    thread.is_living = False
    thread.is_current_focus = False
    thread.last_active_at = utcnow()

    # Close open episodes
    open_episodes = db.query(Episode).filter(Episode.thread_id == thread.id, Episode.ended_at == None).all()
    for ep in open_episodes:
        ep.ended_at = utcnow()
        ep.ending_reason = note or "Thread completed."

    event = Event(
        thread_id=thread.id,
        event_type="CLOSED",
        summary=note or "Thread completed and archived from living radar.",
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def update_thread_frontier(
    db: Session,
    thread_id: int,
    frontier: Optional[str] = None,
    next_action: Optional[str] = None,
    state: Optional[str] = None,
    attention_fit: Optional[str] = None
) -> Thread:
    """Update frontier, next action, or attention fit with transition audit."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    if frontier is not None and frontier.strip():
        thread.frontier = frontier.strip()
    if next_action is not None:
        thread.next_action = next_action.strip() if next_action.strip() else None
    if state is not None and state.strip():
        thread.state = state.strip().upper()
    if attention_fit is not None and attention_fit.strip():
        thread.attention_fit = attention_fit.strip().upper()

    thread.last_active_at = utcnow()

    event = Event(
        thread_id=thread.id,
        event_type="UPDATED",
        summary=f"Frontier updated: {thread.frontier[:80]}..." if len(thread.frontier or '') > 80 else f"Frontier updated: {thread.frontier}",
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def accept_result(
    db: Session,
    thread_id: int,
    note: Optional[str] = None,
    updated_frontier: Optional[str] = None
) -> Thread:
    """Accept an agent or computation output, establishing verified progress."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    thread.state = "ACTIVE"
    thread.last_active_at = utcnow()
    if updated_frontier and updated_frontier.strip():
        thread.frontier = updated_frontier.strip()

    event = Event(
        thread_id=thread.id,
        event_type="ACCEPTED",
        summary=note or "Accepted work output and verified results.",
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def rework_result(
    db: Session,
    thread_id: int,
    feedback: str
) -> Thread:
    """Reject or request rework on an agent or computation result."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    thread.state = "ACTIVE"
    thread.last_active_at = utcnow()
    if feedback and feedback.strip():
        thread.next_action = f"Rework needed: {feedback.strip()}"

    payload = {"feedback": feedback}
    event = Event(
        thread_id=thread.id,
        event_type="REWORK_REQUESTED",
        summary=f"Rework requested: {feedback}",
        payload_json=json.dumps(payload),
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def add_surface(
    db: Session,
    thread_id: int,
    surface_type: str,
    label: str,
    uri: Optional[str] = None,
    local_path: Optional[str] = None,
    provider: Optional[str] = None
) -> Surface:
    """Attach a work surface (repo, branch, chat, file, URL) to a thread."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread #{thread_id} not found.")

    surface = Surface(
        thread_id=thread_id,
        surface_type=surface_type.upper(),
        label=label.strip(),
        uri=uri.strip() if uri and uri.strip() else None,
        local_path=local_path.strip() if local_path and local_path.strip() else None,
        provider=provider.strip() if provider and provider.strip() else None,
        created_at=utcnow(),
        last_used_at=utcnow()
    )
    db.add(surface)
    db.flush()

    event = Event(
        thread_id=thread_id,
        event_type="SURFACE_ADDED",
        summary=f"Surface linked: [{surface.surface_type}] {surface.label}",
        occurred_at=utcnow()
    )
    db.add(event)
    thread.last_active_at = utcnow()
    db.commit()
    db.refresh(surface)
    return surface


def delete_surface(db: Session, surface_id: int) -> bool:
    """Remove a surface pointer."""
    surface = db.query(Surface).filter(Surface.id == surface_id).first()
    if not surface:
        return False
    db.delete(surface)
    db.commit()
    return True


def parse_capture_transcript(db: Session, transcript: str) -> Dict[str, Any]:
    """Parse natural language dictate/transcript into proposed structured transition."""
    text = transcript.strip()
    lower = text.lower()
    
    # 1. Match living thread
    living_threads = db.query(Thread).filter(Thread.is_living == True).all()
    matched_thread = None
    
    for t in living_threads:
        # Match thread name words
        t_name_lower = t.name.lower()
        if t_name_lower in lower:
            matched_thread = t
            break
        # Match project name
        if t.project and t.project.name.lower() in lower:
            matched_thread = t
            break
        # Match significant words in name
        name_words = [w for w in t_name_lower.split() if len(w) > 4]
        if any(w in lower for w in name_words):
            matched_thread = t
            break

    # 2. Detect event type & state
    event_type = "VOICE_NOTE"
    proposed_state = matched_thread.state if matched_thread else "ACTIVE"
    resume_condition = None

    if any(k in lower for k in ["blocked on", "waiting for", "waiting on", "dependency"]):
        event_type = "WAITING"
        proposed_state = "WAITING"
        # Extract after waiting on/for
        for marker in ["waiting for ", "waiting on ", "blocked on "]:
            if marker in lower:
                resume_condition = text[lower.index(marker) + len(marker):].split(".")[0].strip()
                break
    elif any(k in lower for k in ["running", "started run", "launched", "gpu compute", "executing"]):
        event_type = "COMPUTE_STARTED"
        proposed_state = "RUNNING"
    elif any(k in lower for k in ["decided", "decision", "chose", "selected"]):
        event_type = "DECISION"
        proposed_state = "ACTIVE"
    elif any(k in lower for k in ["discovered", "observed", "found that", "test passed", "checkpoint"]):
        event_type = "DISCOVERY"
    elif any(k in lower for k in ["parked", "leaving this", "pause for today", "stopping here"]):
        event_type = "PARKED"
        proposed_state = "PARKED"
    elif any(k in lower for k in ["finished", "completed", "done with"]):
        event_type = "NOTE"

    # 3. Next action heuristic
    proposed_next_action = None
    for marker in ["next:", "next action:", "next move:", "then:"]:
        if marker in lower:
            proposed_next_action = text[lower.index(marker) + len(marker):].strip()
            break

    return {
        "transcript": text,
        "thread_id": matched_thread.id if matched_thread else None,
        "thread_name": matched_thread.name if matched_thread else "New Work Thread",
        "is_new_thread": matched_thread is None,
        "event_type": event_type,
        "proposed_state": proposed_state,
        "proposed_frontier": text,
        "proposed_next_action": proposed_next_action or (matched_thread.next_action if matched_thread else "Articulate next action."),
        "resume_condition": resume_condition or (matched_thread.resume_condition if matched_thread else None)
    }


def commit_capture(db: Session, data: Dict[str, Any]) -> Thread:
    """Commit a confirmed capture interpretation to the database."""
    thread_id = data.get("thread_id")
    transcript = data.get("transcript", "").strip()
    event_type = data.get("event_type", "VOICE_NOTE")
    state = data.get("proposed_state")
    frontier = data.get("proposed_frontier")
    next_action = data.get("proposed_next_action")
    resume_condition = data.get("resume_condition")

    if thread_id:
        thread = db.query(Thread).filter(Thread.id == int(thread_id)).first()
    else:
        # Create new thread
        thread_name = data.get("thread_name") or "New Dictated Thread"
        thread = Thread(
            name=thread_name,
            intent=transcript[:200] if transcript else None,
            frontier=frontier or transcript or "Initial frontier articulated.",
            state=state or "READY",
            attention_fit="FOCUS",
            is_living=True,
            is_current_focus=True,
            created_at=utcnow(),
            last_active_at=utcnow()
        )
        db.query(Thread).filter(Thread.is_current_focus == True).update({"is_current_focus": False})
        db.add(thread)
        db.flush()

    if state:
        thread.state = state
    if frontier:
        thread.frontier = frontier
    if next_action:
        thread.next_action = next_action
    if resume_condition:
        thread.resume_condition = resume_condition

    thread.last_active_at = utcnow()

    event = Event(
        thread_id=thread.id,
        event_type=event_type,
        summary=transcript or f"Recorded transition via universal capture ({event_type}).",
        payload_json=json.dumps({"transcript": transcript, "capture_type": "UNIVERSAL_VOICE"}),
        occurred_at=utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(thread)
    return thread


def log_friction(
    db: Session,
    note: str,
    category: Optional[str] = "FRICTION",
    page_url: Optional[str] = None,
    thread_id: Optional[int] = None
) -> FrictionLog:
    """Record dogfood friction observation."""
    f_log = FrictionLog(
        note=note.strip(),
        category=category.strip().upper() if category else "FRICTION",
        page_url=page_url.strip() if page_url else None,
        thread_id=thread_id,
        created_at=utcnow()
    )
    db.add(f_log)
    db.commit()
    db.refresh(f_log)
    return f_log

