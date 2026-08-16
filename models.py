from datetime import datetime, timezone
import json
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, Float
)
from sqlalchemy.orm import declarative_base, relationship, backref

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    domain = Column(String(50), nullable=False, default="Personal")  # Professional, Research, Creative, Personal
    status = Column(String(50), nullable=False, default="ACTIVE")    # ACTIVE, ARCHIVED, COMPLETED
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    threads = relationship("Thread", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.name} [{self.domain}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "thread_count": len(self.threads) if self.threads else 0,
        }


class Actor(Base):
    __tablename__ = "actors"

    id = Column(Integer, primary_key=True)
    actor_type = Column(String(50), nullable=False)  # HUMAN, AGENT, PROCESS, EXTERNAL_PERSON, SERVICE
    name = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=True)   # Antigravity, ChatGPT, Local, Anthropic, System, etc.
    metadata_json = Column(Text, nullable=True)

    threads = relationship("Thread", back_populates="current_actor")
    events = relationship("Event", back_populates="actor")

    def __repr__(self):
        return f"<Actor {self.name} ({self.actor_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "actor_type": self.actor_type,
            "name": self.name,
            "provider": self.provider,
        }


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    parent_thread_id = Column(Integer, ForeignKey("threads.id"), nullable=True)
    name = Column(String(255), nullable=False)
    intent = Column(Text, nullable=True)
    frontier = Column(Text, nullable=True)
    state = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, NEEDS_YOU, READY, RUNNING, WAITING, PARKED, DONE
    attention_fit = Column(String(50), nullable=True)             # DEEP, BUILD, SUPERVISE, CONSUME, PASSIVE, OPEN
    current_actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    next_action = Column(Text, nullable=True)
    resume_condition = Column(Text, nullable=True)
    is_living = Column(Boolean, default=True, nullable=False)
    is_current_focus = Column(Boolean, default=False, nullable=False)
    working_set_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_active_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    project = relationship("Project", back_populates="threads")
    current_actor = relationship("Actor", back_populates="threads")
    surfaces = relationship("Surface", back_populates="thread", cascade="all, delete-orphan", order_by="Surface.created_at.desc()")
    episodes = relationship("Episode", back_populates="thread", cascade="all, delete-orphan", order_by="Episode.started_at.desc()")
    events = relationship("Event", back_populates="thread", cascade="all, delete-orphan", order_by="Event.occurred_at.asc()")
    work_packets = relationship("WorkPacket", back_populates="thread", cascade="all, delete-orphan", order_by="WorkPacket.created_at.desc()")
    
    subthreads = relationship(
        "Thread",
        backref=backref("parent_thread", remote_side=[id]),
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Thread #{self.id}: {self.name} [{self.state}]>"

    @property
    def active_work_packet(self):
        """Returns the most recent active or reviewing work packet if any."""
        for wp in self.work_packets:
            if wp.status in ("PREPARED", "DISPATCHED", "DELIVERED", "REWORK_REQUESTED"):
                return wp
        return None

    @property
    def queue(self) -> str:
        """Derive cockpit attention queue from thread state."""
        state = (self.state or "ACTIVE").upper()
        if state in ("NEEDS_YOU", "REVIEW"):
            return "NEEDS_YOU"
        if state == "RUNNING":
            return "RUNNING"
        if state in ("READY", "ACTIVE"):
            return "READY"
        if state in ("WAITING", "BLOCKED"):
            return "WAITING"
        if state == "PARKED":
            return "PARKED"
        if state == "DONE":
            return "DONE"
        return "READY"

    @property
    def domain(self) -> str:
        if self.project and self.project.domain:
            return self.project.domain
        return "Personal"

    @property
    def relative_last_active(self) -> str:
        if not self.last_active_at:
            return "never"
        now = datetime.now(timezone.utc)
        diff = now - (self.last_active_at if self.last_active_at.tzinfo else self.last_active_at.replace(tzinfo=timezone.utc))
        secs = int(diff.total_seconds())
        if secs < 60:
            return "just now"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"

    @property
    def is_stale_frontier(self) -> bool:
        """Returns True if thread is living and untouched for >3 days."""
        if not self.is_living or not self.last_active_at:
            return False
        now = datetime.now(timezone.utc)
        last_active = self.last_active_at if self.last_active_at.tzinfo else self.last_active_at.replace(tzinfo=timezone.utc)
        diff = now - last_active
        return diff.total_seconds() > (3 * 86400)

    @property
    def is_cold_storage(self) -> bool:
        """Returns True if thread is parked and untouched for >7 days."""
        if self.state != "PARKED" or not self.last_active_at:
            return False
        now = datetime.now(timezone.utc)
        last_active = self.last_active_at if self.last_active_at.tzinfo else self.last_active_at.replace(tzinfo=timezone.utc)
        diff = now - last_active
        return diff.total_seconds() > (7 * 86400)

    def get_working_set(self) -> Dict[str, Any]:
        """Return parsed working set dictionary."""
        if not self.working_set_json:
            return {}
        try:
            return json.loads(self.working_set_json)
        except Exception:
            return {}

    @property
    def situation_summary(self) -> Dict[str, Any]:
        """NASA Cockpit Situation Strip Model:
        Answers: Where it is -> Who has it -> Why it stopped/state -> What you need to do next -> Supporting evidence.
        """
        ws = self.get_working_set()
        wp = self.active_work_packet
        actor_name = self.current_actor.name if self.current_actor else "Me"
        
        state_label = self.queue
        if self.queue == "NEEDS_YOU":
            state_label = "NEEDS YOU · Human Judgment"
        elif self.queue == "RUNNING":
            state_label = f"RUNNING · {actor_name} Executing"
        elif self.queue == "WAITING":
            state_label = "WAITING · External Condition"
        elif self.queue == "READY":
            state_label = "READY · Work Prepared"
        elif self.state == "PARKED":
            state_label = "PARKED · Inactive"

        # Evidence / Support Telemetry
        support_parts = []
        if ws.get("tests_status"):
            support_parts.append(f"{ws.get('tests_status')}")
        if ws.get("files_changed_count"):
            support_parts.append(f"{ws.get('files_changed_count')} files changed")
        if ws.get("expected_duration") and self.queue == "RUNNING":
            support_parts.append(f"est. {ws.get('expected_duration')}")
        if self.resume_condition and self.queue == "WAITING":
            support_parts.append(f"Blocked by: {self.resume_condition}")
        if wp and wp.stop_conditions:
            support_parts.append(f"Guardrail: {wp.stop_conditions}")

        support_text = " · ".join(support_parts) if support_parts else "Working set nominal"

        return {
            "state_label": state_label,
            "queue": self.queue,
            "headline": self.frontier or "Frontier not articulated.",
            "next_move": self.next_action or "Review active context and specify next move.",
            "actor": actor_name,
            "attention_fit": self.attention_fit or "FOCUS",
            "support": support_text,
            "is_current_focus": self.is_current_focus,
            "last_active": self.relative_last_active
        }

    @property
    def cognitive_cost(self) -> Dict[str, Any]:
        """Calculates cognitive attention cost (Glance, Quick Choice, Deep Focus, Audio)."""
        from domain.attention_scheduler import estimate_thread_attention_cost
        return estimate_thread_attention_cost(self)

    def compile_briefing(self) -> Dict[str, Any]:
        """Deterministic re-entry capsule compiler."""
        recent_events = list(reversed(self.events))[:5] if self.events else []
        last_episode = self.episodes[0] if self.episodes else None
        return {
            "thread_id": self.id,
            "name": self.name,
            "project_name": self.project.name if self.project else None,
            "domain": self.domain,
            "intent": self.intent or "No stated intent.",
            "frontier": self.frontier or "Frontier not defined yet.",
            "why_it_stopped": (last_episode.ending_reason if last_episode and last_episode.ending_reason else self.resume_condition) or "Suspended without explicit blocker.",
            "resume_condition": self.resume_condition,
            "first_move": self.next_action or "Review recent events and determine next action.",
            "attention_fit": self.attention_fit or "FOCUS",
            "actor": self.current_actor.name if self.current_actor else "Me",
            "last_active": self.relative_last_active,
            "is_current_focus": self.is_current_focus,
            "working_set": self.get_working_set(),
            "surfaces": [s.to_dict() for s in self.surfaces],
            "recent_events": [e.to_dict() for e in recent_events],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "domain": self.domain,
            "name": self.name,
            "intent": self.intent,
            "frontier": self.frontier,
            "state": self.state,
            "queue": self.queue,
            "attention_fit": self.attention_fit,
            "current_actor": self.current_actor.name if self.current_actor else None,
            "next_action": self.next_action,
            "resume_condition": self.resume_condition,
            "is_living": self.is_living,
            "is_current_focus": self.is_current_focus,
            "working_set": self.get_working_set(),
            "relative_last_active": self.relative_last_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "surfaces_count": len(self.surfaces),
            "events_count": len(self.events),
        }



class Surface(Base):
    __tablename__ = "surfaces"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=True)
    surface_type = Column(String(50), nullable=False)  # CHAT, IDE, REPOSITORY, BRANCH, FILE, FOLDER, WEBPAGE, NOTEBOOK, AUDIO, TERMINAL, OTHER
    provider = Column(String(100), nullable=True)      # Antigravity, ChatGPT, GitHub, Local, Web, Audio
    label = Column(String(200), nullable=False)
    uri = Column(String(1000), nullable=True)
    external_id = Column(String(255), nullable=True)
    local_path = Column(String(1000), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    thread = relationship("Thread", back_populates="surfaces")

    def __repr__(self):
        return f"<Surface {self.label} [{self.surface_type}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "surface_type": self.surface_type,
            "provider": self.provider,
            "label": self.label,
            "uri": self.uri,
            "local_path": self.local_path,
        }


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    mode = Column(String(50), nullable=True)  # DEEP, BUILD, SUPERVISE, etc.
    summary = Column(Text, nullable=True)
    ending_reason = Column(Text, nullable=True)

    thread = relationship("Thread", back_populates="episodes")
    events = relationship("Event", back_populates="episode")

    def __repr__(self):
        return f"<Episode #{self.id} for Thread #{self.thread_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "mode": self.mode,
            "summary": self.summary,
            "ending_reason": self.ending_reason,
        }


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    event_type = Column(String(50), nullable=False)  # THREAD_CREATED, STARTED, UPDATED, NOTE, DISCOVERY, DECISION, DELEGATED, LAUNCHED, BLOCKED, WAITING, RESULT_READY, REVIEW_REQUESTED, ACCEPTED, PARKED, RESUMED, CLOSED
    occurred_at = Column(DateTime(timezone=True), default=utcnow)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    summary = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=True)
    source_surface_id = Column(Integer, ForeignKey("surfaces.id"), nullable=True)

    thread = relationship("Thread", back_populates="events")
    episode = relationship("Episode", back_populates="events")
    actor = relationship("Actor", back_populates="events")
    source_surface = relationship("Surface")

    def __repr__(self):
        return f"<Event #{self.id}: {self.event_type} on Thread #{self.thread_id}>"

    @property
    def relative_time(self) -> str:
        if not self.occurred_at:
            return ""
        now = datetime.now(timezone.utc)
        diff = now - (self.occurred_at if self.occurred_at.tzinfo else self.occurred_at.replace(tzinfo=timezone.utc))
        secs = int(diff.total_seconds())
        if secs < 60:
            return "just now"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"

    def get_payload(self) -> Dict[str, Any]:
        if not self.payload_json:
            return {}
        try:
            return json.loads(self.payload_json)
        except Exception:
            return {}

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "episode_id": self.episode_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "relative_time": self.relative_time,
            "actor": self.actor.name if self.actor else None,
            "summary": self.summary,
            "payload": self.get_payload(),
        }



class Relation(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True)
    source_type = Column(String(50), nullable=False, default="thread")
    source_id = Column(Integer, nullable=False)
    relation_type = Column(String(50), nullable=False)  # DEPENDS_ON, BLOCKED_BY, SPAWNED_FROM, INFORMED_BY, SUPERSEDES, TESTS, TRANSFORMS_INTO, SHARES_ARTIFACT_WITH, RELATED_TO
    target_type = Column(String(50), nullable=False, default="thread")
    target_id = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def __repr__(self):
        return f"<Relation {self.source_type}:{self.source_id} -{self.relation_type}-> {self.target_type}:{self.target_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "relation_type": self.relation_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "note": self.note,
        }


class FrictionLog(Base):
    __tablename__ = "friction_logs"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False, default="FRICTION")  # FRICTION, MISSING_CAPABILITY, SUGGESTION
    note = Column(Text, nullable=False)
    page_url = Column(String(500), nullable=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def __repr__(self):
        return f"<FrictionLog #{self.id} [{self.category}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "note": self.note,
            "page_url": self.page_url,
            "thread_id": self.thread_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkPacket(Base):
    __tablename__ = "work_packets"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    desired_outcome = Column(Text, nullable=False)
    constraints = Column(Text, nullable=True)
    stop_conditions = Column(Text, nullable=True)
    authority_level = Column(String(50), nullable=False, default="EXECUTE_AND_TEST")  # EXPLORATORY, PROPOSE_DIFF, EXECUTE_AND_TEST
    expected_evidence = Column(String(255), nullable=False, default="Passing test suite & git working set diff")
    review_requirement = Column(String(50), nullable=False, default="MANDATORY_HUMAN_REVIEW")  # MANDATORY_HUMAN_REVIEW, AUTO_ADOPT_IF_GREEN
    status = Column(String(50), nullable=False, default="PREPARED")  # PREPARED, DISPATCHED, DELIVERED, ACCEPTED, REWORK_REQUESTED
    result_summary = Column(Text, nullable=True)
    result_evidence = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    thread = relationship("Thread", back_populates="work_packets")

    def __repr__(self):
        return f"<WorkPacket #{self.id} on Thread #{self.thread_id} [{self.status}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "desired_outcome": self.desired_outcome,
            "constraints": self.constraints,
            "stop_conditions": self.stop_conditions,
            "authority_level": self.authority_level,
            "expected_evidence": self.expected_evidence,
            "review_requirement": self.review_requirement,
            "status": self.status,
            "result_summary": self.result_summary,
            "result_evidence": self.result_evidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ==========================================================================
# Horizon 7: Epistemic Graph & Provenance Models
# ==========================================================================

class EpistemicNode(Base):
    __tablename__ = "epistemic_nodes"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    node_type = Column(String(50), nullable=False)  # CLAIM, DECISION, EVIDENCE, ARTIFACT, SOURCE
    title = Column(String(255), nullable=False)
    statement = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, SUPERSEDED, REFUTED
    payload_json = Column(Text, nullable=True)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    thread = relationship("Thread", backref=backref("epistemic_nodes", cascade="all, delete-orphan"))
    actor = relationship("Actor")

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "node_type": self.node_type,
            "title": self.title,
            "statement": self.statement,
            "confidence": self.confidence,
            "status": self.status,
            "payload": json.loads(self.payload_json) if self.payload_json else {},
            "actor_id": self.actor_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class EpistemicEdge(Base):
    __tablename__ = "epistemic_edges"

    id = Column(Integer, primary_key=True)
    source_node_id = Column(Integer, ForeignKey("epistemic_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("epistemic_nodes.id", ondelete="CASCADE"), nullable=False)
    edge_type = Column(String(50), nullable=False)  # SUPPORTS, CONTRADICTS, SUPERSEDES, DERIVED_FROM, PRODUCED_BY
    weight = Column(Float, default=1.0, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    source_node = relationship("EpistemicNode", foreign_keys=[source_node_id], backref=backref("outgoing_edges", cascade="all, delete-orphan"))
    target_node = relationship("EpistemicNode", foreign_keys=[target_node_id], backref=backref("incoming_edges", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


