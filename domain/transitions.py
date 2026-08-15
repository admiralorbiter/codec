import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Thread, Event, Episode, Actor, utcnow

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
