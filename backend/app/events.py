from __future__ import annotations

import json
from queue import Empty, Queue
from threading import Lock
from typing import Any, Iterator


class EventBroker:
    def __init__(self) -> None:
        self._clients: set[Queue[dict[str, Any]]] = set()
        self._lock = Lock()

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"type": event_type, **payload}
        with self._lock:
            clients = tuple(self._clients)
        for client in clients:
            try:
                client.put_nowait(event)
            except Exception:
                continue

    def stream(self) -> Iterator[str]:
        client: Queue[dict[str, Any]] = Queue(maxsize=100)
        with self._lock:
            self._clients.add(client)
        try:
            yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                try:
                    event = client.get(timeout=18)
                    event_type = event.pop("type")
                    yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
                except Empty:
                    yield ": heartbeat\n\n"
        finally:
            with self._lock:
                self._clients.discard(client)
