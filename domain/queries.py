from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models import Thread, Project, Actor, Event, Surface

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


def get_all_projects(db: Session) -> List[Project]:
    return db.query(Project).filter(Project.status == "ACTIVE").order_by(Project.name).all()


def get_thread_by_id(db: Session, thread_id: int) -> Optional[Thread]:
    return db.query(Thread).filter(Thread.id == thread_id).first()
