import json
import queue
import threading
import time
from typing import Dict, List, Optional, Any

class TelemetryBroadcaster:
    """
    Thread-safe in-memory Pub/Sub broadcaster for Server-Sent Events (SSE).
    Allows open browser tabs to receive live updates with zero polling.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._global_listeners: List[queue.Queue] = []
        self._thread_listeners: Dict[int, List[queue.Queue]] = {}

    def subscribe(self, thread_id: Optional[int] = None) -> queue.Queue:
        """Subscribes a client to SSE updates (global or specific thread)."""
        q = queue.Queue(maxsize=100)
        with self._lock:
            if thread_id is None:
                self._global_listeners.append(q)
            else:
                if thread_id not in self._thread_listeners:
                    self._thread_listeners[thread_id] = []
                self._thread_listeners[thread_id].append(q)
        return q

    def unsubscribe(self, q: queue.Queue, thread_id: Optional[int] = None):
        """Removes a client queue on disconnect."""
        with self._lock:
            if thread_id is None:
                if q in self._global_listeners:
                    self._global_listeners.remove(q)
            else:
                if thread_id in self._thread_listeners and q in self._thread_listeners[thread_id]:
                    self._thread_listeners[thread_id].remove(q)
                    if not self._thread_listeners[thread_id]:
                        del self._thread_listeners[thread_id]

    def broadcast(self, event_type: str, payload: Dict[str, Any], thread_id: Optional[int] = None):
        """Broadcasts an event to all matching subscribers."""
        msg = {
            "event_type": event_type,
            "thread_id": thread_id,
            "timestamp": time.time(),
            "payload": payload
        }
        raw_sse = f"event: {event_type}\ndata: {json.dumps(msg)}\n\n"

        with self._lock:
            # 1. Send to global listeners
            dead_global = []
            for q in self._global_listeners:
                try:
                    q.put_nowait(raw_sse)
                except queue.Full:
                    dead_global.append(q)
            for q in dead_global:
                if q in self._global_listeners:
                    self._global_listeners.remove(q)

            # 2. Send to thread-specific listeners
            if thread_id is not None and thread_id in self._thread_listeners:
                dead_thread = []
                for q in self._thread_listeners[thread_id]:
                    try:
                        q.put_nowait(raw_sse)
                    except queue.Full:
                        dead_thread.append(q)
                for q in dead_thread:
                    if q in self._thread_listeners[thread_id]:
                        self._thread_listeners[thread_id].remove(q)

# Global singleton broadcaster
broadcaster = TelemetryBroadcaster()
