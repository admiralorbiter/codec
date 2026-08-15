import json
import sys
import os
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from config import Config
from models import Base, Thread, Project, Event, Surface
from domain.queries import get_living_threads, get_thread_by_id
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
            packet = deliver_work_packet_result(db, work_packet_id, result_summary=result_summary, evidence=evidence)
            return {'status': 'delivered', 'work_packet': packet.to_dict()}

    def report_progress(self, thread_id: int, step_name: str, current_step: int = 1, total_steps: int = 1, log_snippet: Optional[str] = None) -> Dict[str, Any]:
        """Broadcasts live step-by-step agent execution progress to the user's open browser session."""
        telemetry_payload = {
            "thread_id": thread_id,
            "step_name": step_name,
            "step_index": current_step,
            "total_steps": total_steps,
            "log_snippet": log_snippet or "",
            "actor_name": "Antigravity"
        }
        broadcaster.broadcast("AGENT_TELEMETRY", telemetry_payload, thread_id=thread_id)
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



if __name__ == '__main__':
    server = CodecMCPServer()
    threads = server.list_threads()
    print(f'Codec MCP Server initialized. Found {len(threads)} living threads.')
