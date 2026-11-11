import itertools
import threading
from _thread import lock
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass
class PendingRequest:
    uid: int
    event: threading.Event
    payload: Any = None


class OSCRequestTracker:
    """Thread-safe tracker using never-reused monotonic IDs and FIFO routing queues."""

    def __init__(self) -> None:
        self._lock: lock = threading.Lock()
        self._id_gen: itertools.count[int] = itertools.count(start = 1)  # Strictly unique, never reused
        self._requests: dict[int, PendingRequest] = {}
        self._routing_queues: dict[tuple[Any, ...], deque[int]] = defaultdict(deque)

    def register(self, route_key: tuple[Any, ...]) -> PendingRequest:
        with self._lock:
            uid: int = next(self._id_gen)
            req = PendingRequest(uid=uid, event=threading.Event())
            self._requests[uid] = req
            self._routing_queues[route_key].append(uid)
            return req

    def resolve(self, route_key: tuple[Any, ...], payload: Any) -> int | None:
        """Matches an incoming OSC reply to the oldest pending unique request for that route."""
        with self._lock:
            queue = self._routing_queues.get(route_key)
            while queue:
                uid: int = queue.popleft()
                req: PendingRequest | None = self._requests.get(uid)
                # Ensure the request hasn't already timed out and been cleaned up
                if req is not None:
                    req.payload = payload
                    req.event.set()
                    return uid
            return None

    def cleanup(self, route_key: tuple[Any, ...], uid: int) -> None:
        """Guarantees removal from tracking structures on completion, timeout, or error."""
        with self._lock:
            self._requests.pop(uid, None)
            queue: deque[int] | None = self._routing_queues.get(route_key)
            if queue:
                try:
                    queue.remove(uid)
                except ValueError:
                    pass  # Already popped by resolve()
                if not queue:
                    del self._routing_queues[route_key]
