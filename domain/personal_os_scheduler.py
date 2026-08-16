import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from models import Thread, WorkPacket, Actor, Event, Relation, utcnow
from domain.attention_scheduler import estimate_thread_attention_cost, CognitiveLoad
from domain.reactivation_engine import evaluate_thread_resume_condition

class AuthorityMatrix(str, Enum):
    AUTONOMOUS_SAFE = "AUTONOMOUS_SAFE"           # Pure background compute, tests, linting, context compilation
    SUPERVISED_DISPATCH = "SUPERVISED_DISPATCH"   # Execute work packets with stop conditions, yield at decision gates
    HUMAN_GATED = "HUMAN_GATED"                   # State mutations, git push, deployment, destructive actions

class OperatorState(str, Enum):
    ACTIVE_FOCUS = "ACTIVE_FOCUS"       # Dedicated 1-on-1 human focus (45m+ slots)
    SUPERVISING = "SUPERVISING"         # Gaming / multitasking / intermittent 1m glance checks
    CONSUMING = "CONSUMING"             # Audio listening / reading mode
    OFFLINE_ASLEEP = "OFFLINE_ASLEEP"   # Operator away / overnight compute scheduling


def calculate_system_throughput_telemetry(session: Session) -> Dict[str, Any]:
    """
    Computes global system throughput and human-machine efficiency metrics:
    - total_living_threads: active threads
    - running_processes: active machine tasks
    - packets_delivered_count: work packets completed
    - decision_gates_adopted: decisions resolved
    - attention_minutes_saved: estimated cognitive minutes saved by agent automation
    """
    threads = session.query(Thread).filter(Thread.is_living == True).all()
    packets = session.query(WorkPacket).all()
    events = session.query(Event).all()

    running_count = sum(1 for t in threads if t.queue == "RUNNING")
    needs_you_count = sum(1 for t in threads if t.queue == "NEEDS_YOU")
    ready_count = sum(1 for t in threads if t.queue == "READY")
    waiting_count = sum(1 for t in threads if t.queue == "WAITING")

    delivered_packets = [wp for wp in packets if wp.status in ("DELIVERED", "ADOPTED", "ACCEPTED")]
    decisions = [e for e in events if "DECISION" in e.event_type]

    # Calculate saved attention: each delivered work packet saves ~25 mins of manual coding
    estimated_attention_saved_hours = round(len(delivered_packets) * 0.45, 1)

    return {
        "total_living_threads": len(threads),
        "queue_breakdown": {
            "RUNNING": running_count,
            "NEEDS_YOU": needs_you_count,
            "READY": ready_count,
            "WAITING": waiting_count
        },
        "packets_delivered": len(delivered_packets),
        "decisions_resolved": len(decisions),
        "autonomous_hours_saved": estimated_attention_saved_hours,
        "active_machine_throughput_pct": round((running_count / max(len(threads), 1)) * 100, 1)
    }


def schedule_autonomous_batch(
    session: Session,
    operator_state: str = "SUPERVISING",
    available_attention_minutes: int = 15,
    max_concurrent_agents: int = 4
) -> Dict[str, Any]:
    """
    Personal OS Scheduler:
    Balances human attention budget with autonomous background machine compute.
    Identifies unblocked ready threads and prepares dispatch manifests for autonomous agents.
    """
    op_state = (operator_state or "SUPERVISING").upper()
    living_threads = session.query(Thread).filter(Thread.is_living == True).all()

    dispatched_candidates = []
    staged_for_human = []
    blocked_threads = []

    for t in living_threads:
        # Check if thread is waiting/blocked
        if t.queue == "WAITING":
            is_sat, reason = evaluate_thread_resume_condition(t)
            if not is_sat:
                blocked_threads.append({"thread_id": t.id, "name": t.name, "reason": reason})
                continue

        cost = estimate_thread_attention_cost(t)
        wp = getattr(t, "active_work_packet", None)

        # In OFFLINE or SUPERVISING mode, dispatch autonomous safe tasks
        if op_state in (OperatorState.OFFLINE_ASLEEP.value, OperatorState.SUPERVISING.value):
            if wp and wp.status == "PREPARED" and len(dispatched_candidates) < max_concurrent_agents:
                dispatched_candidates.append({
                    "thread_id": t.id,
                    "thread_name": t.name,
                    "work_packet_id": wp.id,
                    "desired_outcome": wp.desired_outcome,
                    "authority_level": wp.authority_level,
                    "stop_conditions": wp.stop_conditions,
                    "dispatch_mode": "AUTONOMOUS_BACKGROUND"
                })
            elif cost["load"] == CognitiveLoad.DEEP_FOCUS and t.queue != "NEEDS_YOU":
                staged_for_human.append({
                    "thread_id": t.id,
                    "thread_name": t.name,
                    "load": cost["load"],
                    "reason": "Requires dedicated operator focus session"
                })
        elif op_state == OperatorState.ACTIVE_FOCUS.value:
            # When human is in active focus, prioritize decisions and deep architectural tasks
            if t.queue == "NEEDS_YOU" or cost["load"] == CognitiveLoad.DEEP_FOCUS:
                staged_for_human.append({
                    "thread_id": t.id,
                    "thread_name": t.name,
                    "load": cost["load"],
                    "next_action": t.next_action
                })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operator_state": op_state,
        "available_attention_minutes": available_attention_minutes,
        "scheduled_autonomous_dispatches": dispatched_candidates,
        "dispatches_count": len(dispatched_candidates),
        "staged_for_human_review": staged_for_human,
        "staged_count": len(staged_for_human),
        "blocked_threads": blocked_threads
    }
