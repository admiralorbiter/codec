import json
import sys
import os
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from config import Config
from models import Base, Thread, Project, Event, Surface
from domain.queries import get_living_threads, get_thread_by_id, get_thread_relations
from domain.context_router import compile_context_envelope
from domain.transitions import (
    append_event,
    update_thread_frontier,
    park_thread,
    resume_thread,
    set_current_focus,
    accept_result,
    rework_result,
    add_surface,
    create_work_packet,
    deliver_work_packet_result
)
from domain.sse_service import broadcaster

class CodecMCPServer:
    def __init__(self, db_uri: Optional[str] = None):
        self.db_uri = db_uri or Config.SQLALCHEMY_DATABASE_URI
        self.engine = create_engine(self.db_uri)
        self.session_factory = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.session_factory()

    def list_threads(self, domain: Optional[str] = None, include_parked: bool = True) -> List[Dict[str, Any]]:
        with self.get_session() as db:
            threads = get_living_threads(db, domain=domain, include_parked=include_parked)
            return [t.to_dict() for t in threads]

    def get_thread_briefing(self, thread_id: int) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            return thread.compile_briefing()

    def record_update(self, thread_id: int, summary: str, event_type: str = 'NOTE', payload_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self.get_session() as db:
            event = append_event(db, thread_id, event_type=event_type, summary=summary, payload_dict=payload_dict)
            return event.to_dict()

    def record_blocker(self, thread_id: int, blocker_text: str, resume_condition: Optional[str] = None) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            thread.state = 'WAITING'
            if resume_condition:
                thread.resume_condition = resume_condition
            event = append_event(db, thread_id, event_type='BLOCKED', summary=blocker_text, payload_dict={'resume_condition': resume_condition})
            return {'status': 'blocked', 'thread_id': thread_id, 'event': event.to_dict()}

    def record_result(self, thread_id: int, summary: str, updated_frontier: Optional[str] = None) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            thread.state = 'NEEDS_YOU'
            if updated_frontier:
                thread.frontier = updated_frontier
            event = append_event(db, thread_id, event_type='RESULT_READY', summary=summary)
            return {'status': 'result_ready', 'thread_id': thread_id, 'event': event.to_dict()}

    def request_review(self, thread_id: int, decision_title: str, options: List[Dict[str, Any]], estimated_attention: str = '2-5 min') -> Dict[str, Any]:
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            thread.state = 'NEEDS_YOU'
            payload = {
                'decision_title': decision_title,
                'estimated_attention': estimated_attention,
                'options': options
            }
            event = append_event(db, thread_id, event_type='DECISION_REQUIRED', summary=f'DECISION GATE: {decision_title}', payload_dict=payload)
            return {'status': 'decision_required', 'thread_id': thread_id, 'event': event.to_dict()}

    def update_frontier(self, thread_id: int, frontier: Optional[str] = None, next_action: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = update_thread_frontier(db, thread_id, frontier=frontier, next_action=next_action, state=state)
            return thread.to_dict()

    def park(self, thread_id: int, note: Optional[str] = None, resume_condition: Optional[str] = None) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = park_thread(db, thread_id, note=note, resume_condition=resume_condition)
            return thread.to_dict()

    def resume(self, thread_id: int) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = resume_thread(db, thread_id)
            return thread.to_dict()

    def get_active_work_packet(self, thread_id: int) -> Dict[str, Any]:
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            wp = getattr(thread, "active_work_packet", None)
            if not wp:
                return {'status': 'none', 'message': 'No active work packet found on thread.'}
            return {'status': 'ok', 'work_packet': wp.to_dict()}

    def deliver_work_packet(self, thread_id: int, work_packet_id: int, result_summary: str, evidence: Optional[str] = None) -> Dict[str, Any]:
        with self.get_session() as db:
            packet = deliver_work_packet_result(db, work_packet_id, result_summary=result_summary, evidence=evidence, thread_id=thread_id)
            return {'status': 'delivered', 'work_packet': packet.to_dict()}

    def report_progress(self, thread_id: int, step_name: str, current_step: int = 1, total_steps: int = 1, log_snippet: Optional[str] = None) -> Dict[str, Any]:
        """Broadcasts live step-by-step agent execution progress across processes to the user's browser."""
        telemetry_payload = {
            "thread_id": thread_id,
            "step_name": step_name,
            "step_index": current_step,
            "total_steps": total_steps,
            "log_snippet": log_snippet or "",
            "actor_name": "Antigravity"
        }

        # 1. In-process broadcast (for test suites and embedded servers)
        broadcaster.broadcast("AGENT_TELEMETRY", telemetry_payload, thread_id=thread_id)

        # 2. Post to local HTTP API for cross-process SSE broadcast to browser
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://127.0.0.1:5050/api/agent/telemetry",
                data=json.dumps(telemetry_payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:5050"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                pass
        except Exception:
            pass

        return {'status': 'broadcasted', 'telemetry': telemetry_payload}

    def sync_active_session(self, thread_id: int, active_file: str, current_task: Optional[str] = None) -> Dict[str, Any]:
        """Updates active file working set and records agent context sync event."""
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            ws = thread.get_working_set()
            ws['active_file'] = active_file
            if current_task:
                ws['current_task'] = current_task
            thread.working_set_json = json.dumps(ws)
            event = append_event(
                db,
                thread_id,
                event_type="AGENT_SYNC",
                summary=f"Antigravity working on `{active_file}`: {current_task or 'Active editing'}",
                payload_dict={"active_file": active_file, "current_task": current_task}
            )
            return {'status': 'synced', 'working_set': ws, 'event': event.to_dict()}

    def compile_context(self, thread_id: int, target: str = 'ANTIGRAVITY', budget: str = 'STANDARD') -> Dict[str, Any]:
        with self.get_session() as db:
            thread = get_thread_by_id(db, thread_id)
            if not thread:
                return {'error': f'Thread #{thread_id} not found'}
            relations = get_thread_relations(db, thread_id)
            return compile_context_envelope(thread, target=target, budget=budget, relations=relations)

    def get_os_status(self) -> Dict[str, Any]:
        from domain.personal_os_scheduler import calculate_system_throughput_telemetry
        with self.get_session() as db:
            return calculate_system_throughput_telemetry(db)

    def schedule_batch(self, operator_state: str = 'SUPERVISING', available_attention_minutes: int = 15) -> Dict[str, Any]:
        from domain.personal_os_scheduler import schedule_autonomous_batch
        with self.get_session() as db:
            return schedule_autonomous_batch(db, operator_state=operator_state, available_attention_minutes=available_attention_minutes)


# -------------------------------------------------------------
# Standard MCP JSON-RPC 2.0 Stdio Transport Protocol Loop
# -------------------------------------------------------------

def run_mcp_stdio_server(db_uri: Optional[str] = None):
    """
    Standard MCP stdio transport loop. Listens on stdin and writes JSON-RPC 2.0 to stdout.
    Compatible with Antigravity, Claude Desktop, and standard MCP clients.
    """
    server = CodecMCPServer(db_uri=db_uri)

    tools_spec = [
        {
            "name": "list_threads",
            "description": "Lists active threads from Codec cognitive control plane.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Optional domain filter (Professional, Research, Creative, Personal)"},
                    "include_parked": {"type": "boolean", "default": True}
                }
            }
        },
        {
            "name": "get_thread_briefing",
            "description": "Retrieves the full cognitive briefing capsule for a thread (frontier, next move, why work stopped, working set).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"}
                },
                "required": ["thread_id"]
            }
        },
        {
            "name": "get_active_work_packet",
            "description": "Reads the active delegated work packet with stop conditions and authority level.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"}
                },
                "required": ["thread_id"]
            }
        },
        {
            "name": "report_progress",
            "description": "Broadcasts live step-by-step agent execution progress and test output to the user's open cockpit tab in real time.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"},
                    "step_name": {"type": "string", "description": "Current action being performed (e.g. 'Running pytest suite')"},
                    "current_step": {"type": "integer", "default": 1},
                    "total_steps": {"type": "integer", "default": 1},
                    "log_snippet": {"type": "string", "description": "Recent output tail or test results"}
                },
                "required": ["thread_id", "step_name"]
            }
        },
        {
            "name": "deliver_work_packet",
            "description": "Delivers completed work packet results with evidence into Codec and requests human review in NEEDS_YOU.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"},
                    "work_packet_id": {"type": "integer", "description": "Work Packet ID"},
                    "result_summary": {"type": "string", "description": "Summary of delivered changes"},
                    "evidence": {"type": "string", "description": "Evidence (test stdout, diff stats)"}
                },
                "required": ["thread_id", "work_packet_id", "result_summary"]
            }
        },
        {
            "name": "update_frontier",
            "description": "Updates the frontier description and immediate first move on a thread.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"},
                    "frontier": {"type": "string", "description": "Updated frontier state"},
                    "next_action": {"type": "string", "description": "Immediate concrete next move"}
                },
                "required": ["thread_id"]
            }
        },
        {
            "name": "sync_active_session",
            "description": "Syncs the active file and task into the thread's working set.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"},
                    "active_file": {"type": "string", "description": "Active relative file path"},
                    "current_task": {"type": "string", "description": "Short description of current task"}
                },
                "required": ["thread_id", "active_file"]
            }
        },
        {
            "name": "compile_context_envelope",
            "description": "Compiles a token-budgeted, target-optimized prompt envelope for Antigravity, ChatGPT, Claude, Local Agent, or Audio Digest.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "integer", "description": "Thread ID"},
                    "target": {"type": "string", "enum": ["ANTIGRAVITY", "CHATGPT", "CLAUDE", "LOCAL_AGENT", "AUDIO_DIGEST"], "description": "Target AI agent or model"},
                    "budget": {"type": "string", "enum": ["COMPACT", "STANDARD", "EXHAUSTIVE"], "description": "Token budget size"}
                },
                "required": ["thread_id"]
            }
        },
        {
            "name": "get_operating_system_status",
            "description": "Horizon 8: Returns global system throughput, active processes, delivered packets, and attention savings.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "schedule_autonomous_batch",
            "description": "Horizon 8: Evaluates human attention budget vs machine compute and returns an autonomous execution schedule.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operator_state": {"type": "string", "enum": ["ACTIVE_FOCUS", "SUPERVISING", "CONSUMING", "OFFLINE_ASLEEP"], "default": "SUPERVISING"},
                    "available_attention_minutes": {"type": "integer", "default": 15},
                    "max_concurrent_agents": {"type": "integer", "default": 4}
                }
            }
        }
    ]

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "codec-control-plane", "version": "0.8.0"}
                    }
                }
            elif method == "notifications/initialized":
                continue
            elif method == "ping":
                res = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            elif method == "tools/list":
                res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_spec}}
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})

                if tool_name == "list_threads":
                    out = server.list_threads(domain=args.get("domain"), include_parked=args.get("include_parked", True))
                elif tool_name == "get_thread_briefing":
                    out = server.get_thread_briefing(thread_id=args.get("thread_id"))
                elif tool_name == "get_active_work_packet":
                    out = server.get_active_work_packet(thread_id=args.get("thread_id"))
                elif tool_name == "compile_context_envelope":
                    out = server.compile_context(
                        thread_id=args.get("thread_id"),
                        target=args.get("target", "ANTIGRAVITY"),
                        budget=args.get("budget", "STANDARD")
                    )
                elif tool_name == "get_operating_system_status":
                    out = server.get_os_status()
                elif tool_name == "schedule_autonomous_batch":
                    out = server.schedule_batch(
                        operator_state=args.get("operator_state", "SUPERVISING"),
                        available_attention_minutes=args.get("available_attention_minutes", 15)
                    )
                elif tool_name == "report_progress":
                    out = server.report_progress(
                        thread_id=args.get("thread_id"),
                        step_name=args.get("step_name"),
                        current_step=args.get("current_step", 1),
                        total_steps=args.get("total_steps", 1),
                        log_snippet=args.get("log_snippet")
                    )
                elif tool_name == "deliver_work_packet":
                    out = server.deliver_work_packet(
                        thread_id=args.get("thread_id"),
                        work_packet_id=args.get("work_packet_id"),
                        result_summary=args.get("result_summary"),
                        evidence=args.get("evidence")
                    )
                elif tool_name == "update_frontier":
                    out = server.update_frontier(
                        thread_id=args.get("thread_id"),
                        frontier=args.get("frontier"),
                        next_action=args.get("next_action")
                    )
                elif tool_name == "sync_active_session":
                    out = server.sync_active_session(
                        thread_id=args.get("thread_id"),
                        active_file=args.get("active_file"),
                        current_task=args.get("current_task")
                    )
                else:
                    out = {"error": f"Unknown tool: {tool_name}"}

                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(out)}]
                    }
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"}
                }

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal MCP server error: {str(e)}"}
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == '__main__':
    run_mcp_stdio_server()

