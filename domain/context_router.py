from enum import Enum
from typing import Optional, Dict, Any, List
import re

class TargetProfile(str, Enum):
    ANTIGRAVITY = "ANTIGRAVITY"
    CHATGPT = "CHATGPT"
    CLAUDE = "CLAUDE"
    LOCAL_AGENT = "LOCAL_AGENT"
    AUDIO_DIGEST = "AUDIO_DIGEST"

class TokenBudget(str, Enum):
    COMPACT = "COMPACT"          # ~150-250 tokens (immediate next tactical move)
    STANDARD = "STANDARD"        # ~500-750 tokens (full operational context)
    EXHAUSTIVE = "EXHAUSTIVE"    # ~1200-1800 tokens (full history, episodes, relations)

def estimate_tokens(text: str) -> int:
    """Fast rule-of-thumb token estimator (~4 characters per token)."""
    if not text:
        return 0
    words = len(re.findall(r'\w+|[^\w\s]', text, re.UNICODE))
    return int(words * 1.3)

def compile_context_envelope(
    thread: Any,
    target: str = "ANTIGRAVITY",
    budget: str = "STANDARD",
    include_relations: bool = True,
    relations: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Compiles a target-optimized, token-budgeted prompt envelope
    designed for zero-friction handoff to fresh models or agents.
    
    Principles:
    - Store richly, compile sparingly.
    - Tailored to target agent capabilities and prompt formats.
    """
    tgt = target.upper() if target else "ANTIGRAVITY"
    if tgt not in TargetProfile.__members__:
        tgt = "ANTIGRAVITY"
    
    bgt = budget.upper() if budget else "STANDARD"
    if bgt not in TokenBudget.__members__:
        bgt = "STANDARD"

    project_name = thread.project.name if thread.project else "General"
    ws = thread.get_working_set() if hasattr(thread, "get_working_set") else {}
    wp = getattr(thread, "active_work_packet", None)
    
    # Target-Specific Compilers
    if tgt == TargetProfile.AUDIO_DIGEST:
        content = _compile_audio_digest(thread, project_name, ws, wp, bgt, relations)
    elif tgt == TargetProfile.ANTIGRAVITY:
        content = _compile_antigravity_profile(thread, project_name, ws, wp, bgt, relations)
    elif tgt == TargetProfile.CHATGPT:
        content = _compile_chatgpt_profile(thread, project_name, ws, wp, bgt, relations)
    elif tgt == TargetProfile.CLAUDE:
        content = _compile_claude_profile(thread, project_name, ws, wp, bgt, relations)
    else:  # LOCAL_AGENT
        content = _compile_local_agent_profile(thread, project_name, ws, wp, bgt)

    token_count = estimate_tokens(content)

    return {
        "thread_id": thread.id,
        "thread_name": thread.name,
        "target": tgt,
        "budget": bgt,
        "token_estimate": token_count,
        "content": content
    }


def _compile_antigravity_profile(thread: Any, project_name: str, ws: dict, wp: Any, budget: str, relations: Optional[List[Any]]) -> str:
    """Antigravity target: Structured with tools, workspace paths, stop conditions, and test validation."""
    lines = [
        f"# AGENT TASK DIRECTIVE // [{project_name.upper()}] {thread.name} (#{thread.id})",
        "",
        "## 1. Operating State & Intent",
        f"- **Thread Intent**: {thread.intent or 'Deliver core thread objectives.'}",
        f"- **Current State**: `{thread.state}` ({thread.queue}) | Mode: `{thread.attention_fit or 'FOCUS'}`",
        f"- **Current Frontier**: {thread.frontier or 'Frontier not articulated yet.'}",
    ]

    if thread.next_action:
        lines.append(f"- **Immediate First Action**: {thread.next_action}")

    # Working Set
    if ws:
        lines.extend([
            "",
            "## 2. Local Workspace & Git Context",
            f"- **Repository**: `{ws.get('repo', 'local')}` (Path: `{ws.get('repo_path', '.')}`)",
            f"- **Active Branch**: `{ws.get('branch', 'main')}` @ `{ws.get('commit', 'head')}`",
        ])
        if ws.get("files_changed_count"):
            lines.append(f"- **Working Tree**: {ws.get('files_changed_count')} modified files (+{ws.get('additions', 0)}/-{ws.get('deletions', 0)})")
        if ws.get("tests_status"):
            lines.append(f"- **Test Suite Telemetry**: `{ws.get('tests_status')}`")

    # Work Packet & Guardrails
    if wp:
        lines.extend([
            "",
            f"## 3. Delegated Work Packet (#{wp.id})",
            f"- **Authority Level**: `{wp.authority_level}`",
            f"- **Desired Outcome**: {wp.desired_outcome}",
        ])
        if wp.constraints:
            lines.append(f"- **Explicit Constraints**: {wp.constraints}")
        if wp.stop_conditions:
            lines.append(f"- **STOP CONDITIONS (Yield control if encountered)**: {wp.stop_conditions}")
        if wp.expected_evidence:
            lines.append(f"- **Expected Evidence**: {wp.expected_evidence}")
        if wp.status == "REWORK_REQUESTED" and wp.result_evidence:
            lines.append(f"- **Rework Directive**: {wp.result_summary}")

    # Related Cross-Thread Context (Standard & Exhaustive)
    if budget in (TokenBudget.STANDARD, TokenBudget.EXHAUSTIVE) and relations:
        rel_lines = []
        for r in relations:
            name = getattr(r, "other_thread_name", None) or f"Thread #{getattr(r, 'other_thread_id', '?')}"
            rel_lines.append(f"- `[{getattr(r, 'relation_type', 'LINKED')}]` {name}: {getattr(r, 'note', '') or 'Dependency'}")
        if rel_lines:
            lines.extend(["", "## 4. Cross-Thread Dependencies", *rel_lines])

    # Horizon 7: Provenance & Verified Claims (Standard & Exhaustive)
    if hasattr(thread, "epistemic_nodes") and thread.epistemic_nodes:
        claims = [n for n in thread.epistemic_nodes if getattr(n, "node_type", "") == "CLAIM" and getattr(n, "status", "") == "ACTIVE"]
        if claims:
            lines.extend(["", "## 5. Provenance & Verified Claims"])
            for c in claims[:4]:
                lines.append(f"- **{c.title}**: {c.statement}")

    # Deep History / Episodes (Exhaustive only)
    if budget == TokenBudget.EXHAUSTIVE and hasattr(thread, "events"):
        recent_events = [e for e in thread.events[-8:]]
        if recent_events:
            lines.extend(["", "## 6. Recent Activity Stream"])
            for e in recent_events:
                lines.append(f"- `[{e.event_type}]` {e.summary}")

    lines.extend([
        "",
        "## Agent Instructions",
        "1. Proceed strictly from the current frontier above.",
        "2. Adhere to stop conditions and verify all changes against the test suite.",
        "3. Provide atomic diffs and clear evidence upon completion."
    ])

    return "\n".join(lines)


def _compile_chatgpt_profile(thread: Any, project_name: str, ws: dict, wp: Any, budget: str, relations: Optional[List[Any]]) -> str:
    """ChatGPT target: Focuses on mental model, architectural trade-offs, and decision reasoning."""
    lines = [
        f"You are collaborating on project **{project_name}** on thread **{thread.name}**.",
        "",
        f"### Stated Intent\n{thread.intent or 'Advance thread architecture.'}",
        "",
        f"### Where Work Currently Left Off (Frontier)\n{thread.frontier}",
    ]

    if thread.next_action:
        lines.append(f"\n### Proposed Next Move\n{thread.next_action}")

    # Recent Decisions / Constraints
    if hasattr(thread, "events"):
        decisions = [e for e in thread.events if "DECISION" in e.event_type]
        if decisions:
            lines.append("\n### Key Architectural Decisions Made")
            for d in decisions[-3:]:
                lines.append(f"- {d.summary}")

    if wp and wp.constraints:
        lines.append(f"\n### Core Architectural Constraints\n- {wp.constraints}")

    if budget in (TokenBudget.STANDARD, TokenBudget.EXHAUSTIVE) and relations:
        lines.append("\n### Related Threads in Graph")
        for r in relations:
            name = getattr(r, "other_thread_name", None) or f"Thread #{getattr(r, 'other_thread_id', '?')}"
            lines.append(f"- {name} ({getattr(r, 'relation_type', 'LINKED')}): {getattr(r, 'note', '')}")

    lines.extend([
        "",
        "### Request",
        "Please analyze the situation above. Reason through any trade-offs, identify edge cases, and propose the cleanest implementation strategy."
    ])

    return "\n".join(lines)


def _compile_claude_profile(thread: Any, project_name: str, ws: dict, wp: Any, budget: str, relations: Optional[List[Any]]) -> str:
    """Claude target: Code-centric with exact file boundaries and concrete diff expectations."""
    lines = [
        f"# Context Envelope: [{project_name}] {thread.name}",
        f"<frontier>{thread.frontier}</frontier>",
        f"<next_action>{thread.next_action or 'Implement solution'}</next_action>",
    ]

    if ws:
        lines.append(f"<working_set repo='{ws.get('repo', '')}' branch='{ws.get('branch', '')}' tests='{ws.get('tests_status', '')}'/>")

    if wp:
        lines.extend([
            "<work_packet>",
            f"  <outcome>{wp.desired_outcome}</outcome>",
            f"  <stop_conditions>{wp.stop_conditions or 'None'}</stop_conditions>",
            f"  <evidence>{wp.expected_evidence or 'Passing unit tests'}</evidence>",
            "</work_packet>"
        ])

    if budget == TokenBudget.EXHAUSTIVE and hasattr(thread, "events"):
        diff_events = [e for e in thread.events if e.event_type in ("GIT_DIFF", "GIT_COMMIT")]
        if diff_events:
            lines.append("<recent_commits>")
            for de in diff_events[-3:]:
                lines.append(f"  <commit>{de.summary}</commit>")
            lines.append("</recent_commits>")

    lines.extend([
        "",
        "Please write clean, type-hinted code satisfying the desired outcome and evidence requirements above."
    ])

    return "\n".join(lines)


def _compile_local_agent_profile(thread: Any, project_name: str, ws: dict, wp: Any, budget: str) -> str:
    """Local Agent profile: Ultra-compact, lowest possible token count for fast execution."""
    wp_str = f" | GOAL: {wp.desired_outcome} | STOP: {wp.stop_conditions}" if wp else ""
    return (
        f"[{project_name}#{thread.id}] {thread.name}\n"
        f"FRONTIER: {thread.frontier}\n"
        f"NEXT: {thread.next_action or 'Proceed'}\n"
        f"GIT: {ws.get('repo', '')}@{ws.get('branch', '')} ({ws.get('tests_status', 'no-tests')})"
        f"{wp_str}"
    )


def _compile_audio_digest(thread: Any, project_name: str, ws: dict, wp: Any, budget: str, relations: Optional[List[Any]]) -> str:
    """Audio Digest profile: Natural conversational narrative for text-to-speech listening while gaming or away."""
    lines = [
        f"Here is your audio brief for {thread.name}, in project {project_name}.",
        "",
        f"Where you left it: {thread.frontier}",
    ]

    if thread.next_action:
        lines.append(f"Your immediate next move is: {thread.next_action}.")

    if ws and ws.get("tests_status"):
        lines.append(f"The local test suite is currently reporting {ws.get('tests_status')}.")

    if wp:
        lines.append(f"There is an active work packet with the goal to {wp.desired_outcome}. The system will stop if {wp.stop_conditions or 'it completes safely'}.")

    if relations:
        lines.append(f"This thread is linked to {len(relations)} other project streams.")

    lines.append("You are in a nominal state to proceed whenever you're ready.")
    return " ".join(lines)
