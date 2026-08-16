from enum import Enum
from typing import Dict, Any, List, Optional

class CognitiveLoad(str, Enum):
    GLANCE = "GLANCE"                 # <= 1 min (nominal status check, 1-click adoption)
    QUICK_CHOICE = "QUICK_CHOICE"     # 2–5 min (PAIR decision gate, choice selection)
    DEEP_FOCUS = "DEEP_FOCUS"         # 30m+ (complex implementation plan, architecture fork)
    AUDIO_CONSUMPTION = "AUDIO"       # 10–20 min (synthesized brief, podcast, passive listening)

def estimate_thread_attention_cost(thread: Any) -> Dict[str, Any]:
    """
    Computes the cognitive attention requirement for a thread based on
    its active queue, decision gates, work packet status, and working set diffs.
    """
    queue = getattr(thread, "queue", "READY")
    ws = thread.get_working_set() if hasattr(thread, "get_working_set") else {}
    wp = getattr(thread, "active_work_packet", None)
    attention_fit = getattr(thread, "attention_fit", "FOCUS")

    # 1. Passive / Audio Consumption mode
    if attention_fit == "CONSUME":
        return {
            "load": CognitiveLoad.AUDIO_CONSUMPTION,
            "minutes": 15,
            "badge_icon": "🎧",
            "badge_label": "15m Audio",
            "css_class": "cog-audio",
            "explanation": "Synthesized audio brief or research material ready for passive listening."
        }

    # 2. Decision Required / Needs You (Check if simple fork vs complex review)
    if queue == "NEEDS_YOU":
        # Check if thread has an active DECISION_REQUIRED event with options
        has_decision_gate = False
        if hasattr(thread, "events"):
            for e in thread.events:
                if e.event_type == "DECISION_REQUIRED":
                    has_decision_gate = True
                    break

        if has_decision_gate:
            return {
                "load": CognitiveLoad.QUICK_CHOICE,
                "minutes": 3,
                "badge_icon": "⚡",
                "badge_label": "2–5m Decision",
                "css_class": "cog-quick",
                "explanation": "Interactive decision gate with pre-calculated trade-offs."
            }

        # Work packet delivered awaiting human review
        if wp and wp.status == "DELIVERED":
            return {
                "load": CognitiveLoad.GLANCE,
                "minutes": 1,
                "badge_icon": "👀",
                "badge_label": "1m Review",
                "css_class": "cog-glance",
                "explanation": "Delivered work packet with test evidence ready for 1-click adoption."
            }

        return {
            "load": CognitiveLoad.QUICK_CHOICE,
            "minutes": 4,
            "badge_icon": "⚡",
            "badge_label": "3–5m Review",
            "css_class": "cog-quick",
            "explanation": "Human judgment required to advance frontier."
        }

    # 3. Running / Machine Execution (Low human attention load)
    if queue == "RUNNING":
        return {
            "load": CognitiveLoad.GLANCE,
            "minutes": 0.5,
            "badge_icon": "👀",
            "badge_label": "30s Glance",
            "css_class": "cog-glance",
            "explanation": "Autonomous compute or agent executing. Zero active human intervention required."
        }

    # 4. Waiting / Blocked
    if queue == "WAITING":
        return {
            "load": CognitiveLoad.GLANCE,
            "minutes": 0.5,
            "badge_icon": "⏸",
            "badge_label": "Waiting",
            "css_class": "cog-waiting",
            "explanation": f"Blocked on external condition: {getattr(thread, 'resume_condition', 'External event')}."
        }

    # 5. Ready / Active Threads (Evaluate diff size and plan complexity)
    files_changed = ws.get("files_changed_count", 0) if ws else 0
    if files_changed > 6 or (wp and wp.authority_level == "EXPLORATORY"):
        return {
            "load": CognitiveLoad.DEEP_FOCUS,
            "minutes": 45,
            "badge_icon": "🧠",
            "badge_label": "45m+ Deep",
            "css_class": "cog-deep",
            "explanation": "Broad working set or exploratory refactor requiring sustained deep focus."
        }

    return {
        "load": CognitiveLoad.QUICK_CHOICE,
        "minutes": 5,
        "badge_icon": "⚡",
        "badge_label": "5m Tactical",
        "css_class": "cog-quick",
        "explanation": "Ready for tactical implementation move."
    }


def filter_and_rank_by_attention(
    threads: List[Any],
    mode: str = "ALL",
    attention_slice: Optional[str] = None
) -> Dict[str, Any]:
    """
    Slices and ranks threads based on cognitive mode and attention filters.
    Provides a separate staging buffer for deep-work tasks when in SUPERVISE mode.
    """
    mode = (mode or "ALL").upper()
    slice_filter = (attention_slice or "ALL").upper()

    active_threads = []
    staged_deep_work = []

    for t in threads:
        cost = estimate_thread_attention_cost(t)
        t._cached_cognitive_cost = cost

        # Manual slice filter (if set by user)
        if slice_filter == "GLANCE" and cost["load"] not in (CognitiveLoad.GLANCE, CognitiveLoad.AUDIO_CONSUMPTION):
            continue
        elif slice_filter == "QUICK" and cost["load"] != CognitiveLoad.QUICK_CHOICE:
            continue
        elif slice_filter == "DEEP" and cost["load"] != CognitiveLoad.DEEP_FOCUS:
            continue

        # Mode-based routing
        if mode == "SUPERVISE":
            # In SUPERVISE mode: Deep Focus tasks are moved to the staging buffer
            if cost["load"] == CognitiveLoad.DEEP_FOCUS and getattr(t, "queue", "") != "NEEDS_YOU":
                staged_deep_work.append(t)
            else:
                active_threads.append(t)
        elif mode == "FOCUS":
            # In FOCUS mode: Sort Deep Focus and Decisions to the top
            active_threads.append(t)
        elif mode == "CONSUME":
            # In CONSUME mode: Prioritize Audio and Reading
            active_threads.append(t)
        else:
            active_threads.append(t)

    # Sort active threads by attention priority
    if mode == "SUPERVISE":
        # Needs You first, then Running, then Ready Glance
        active_threads.sort(key=lambda t: (
            0 if getattr(t, "queue", "") == "NEEDS_YOU" else
            (1 if getattr(t, "queue", "") == "RUNNING" else 2)
        ))
    elif mode == "FOCUS":
        # Deep focus and decisions first
        active_threads.sort(key=lambda t: (
            0 if getattr(t, "queue", "") == "NEEDS_YOU" else
            (1 if getattr(t, "_cached_cognitive_cost", {}).get("load") == CognitiveLoad.DEEP_FOCUS else 2)
        ))

    return {
        "active_threads": active_threads,
        "staged_deep_work": staged_deep_work,
        "staged_count": len(staged_deep_work),
        "mode": mode,
        "attention_slice": slice_filter
    }
