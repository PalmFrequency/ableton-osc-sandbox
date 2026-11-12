import itertools
import threading
from _thread import lock
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

# =====================================================================
# OVERVIEW FOR BEGINNERS: WHAT PROBLEM DOES THIS CODE SOLVE?
# =====================================================================
# OSC (Open Sound Control) is a network protocol used by audio/visual
# software (like TouchDesigner, Max/MSP, or digital mixers).
#
# Network communication happens across multiple "threads" (parallel tasks):
#   1. SENDER THREAD: Your main program sends a message out over the network
#      and wants to pause and wait for an answer.
#   2. LISTENER THREAD: A background task constantly listens to the network
#      for incoming replies.
#
# Because OSC doesn't natively attach a "reply ID" to messages, if you send
# two identical requests quickly, you need a way to match the incoming
# replies to the right waiting threads without them crashing into each other.
# This file solves that problem safely.
# =====================================================================

"""

How This Works in Practice (Lifecycle Example with hello_ableton_osc2.py)

To help visualize how two threads use this class together, here is how a typical request is written:
1. Sender Thread calls req = tracker.register(('/get/status',)) to get a ticket.
2. Sender Thread sends the actual OSC network message.
3. Sender Thread calls req.event.wait(timeout=2.0). It freezes here, using zero CPU, waiting for the green light.
4. Listener Thread (running in the background) receives an OSC message from the network on /get/status with data "OK".
5. Listener Thread calls tracker.resolve(('/get/status',), "OK"). This puts "OK" into req.payload and flips req.event to green.
6. Sender Thread immediately wakes up, reads req.payload ("OK"), and calls tracker.cleanup(...) to tidy up memory.

"""

@dataclass
class PendingRequest:
    """
    A container holding the state of a single outgoing request that is
    currently waiting for a reply.
    """

    # A unique ID number assigned to this specific request (e.g., 1, 2, 3...).
    uid: int

    # THREADING CONCEPT: 
    # threading.Event() -> CREATE THE TRAFFIC LIGHT
    # event.wait() -> RED LIGHT (STOP and wait)
    # event.set() -> GREEN LIGHT (OK to proceed)
    #
    # Think of an Event as a TRAFFIC LIGHT that starts RED (unset).
    # - The Sender Thread calls `event.wait()`, which pauses that thread at
    #   the red light so it doesn't waste CPU power checking in a loop.
    # - When a reply arrives, the Listener Thread calls `event.set()`, turning
    #   the light GREEN and immediately waking up the Sender Thread.
    event: threading.Event

    # Once the reply arrives, the Listener Thread stores the answer data here
    # so the Sender Thread can read it after waking up.
    payload: Any = None


class OSCRequestTracker:
    """
    A thread-safe manager that tracks outgoing OSC requests and matches
    incoming replies to the oldest waiting request for a given OSC address.
    """

    def __init__(self) -> None:
        # THREADING CONCEPT: threading.Lock()
        # When two threads read and modify the same dictionary or list at the
        # exact same microsecond, data gets corrupted (a "race condition").
        # A Lock is like a bathroom key: only ONE thread can hold it at a time.
        # Any other thread trying to acquire it must wait in line until the
        # first thread finishes and releases it.
        self._lock: lock = threading.Lock()

        # Creates an infinite counter: 1, 2, 3, 4...
        # Because numbers are never reused, an old, delayed reply can never
        # accidentally get confused with a brand-new request.
        self._id_gen: itertools.count[int] = itertools.count(start = 1)

        # A master lookup dictionary mapping:
        #   { unique_id : PendingRequest_object }
        self._requests: dict[int, PendingRequest] = {}

        # A dictionary of zero or more DOUBLE-ENDED QUEUES, grouped by OSC 
        # route/address which may refer to multiple instances described by
        # the same routing address and args.
        # For example, route_key might be ('/mixer/volume', 1).
        # `deque` (double-ended queue) is a list optimized for adding items to
        # the right (`append`) and removing them from the left (`popleft`),
        # creating a strict First-In, First-Out (FIFO) waiting line.
        # Note: There could be two or more requests for the same address
        # but they will be matched to replies in the order they were registered.
        self._routing_queues: dict[tuple[Any, ...], deque[int]] = defaultdict(deque)

    def register(self, route_key: tuple[Any, ...]) -> PendingRequest:
        """
        Called by the SENDER THREAD right BEFORE sending an OSC message.
        It creates a ticket so the thread has something to wait on.
        """
        # `with self._lock:` automatically grabs the "bathroom key" before
        # running the indented code, and guarantees it gives the key back
        # when the block finishes (even if an error occurs).
        with self._lock:
            # 1. Generate the next unique ID number (e.g., 1).
            uid: int = next(self._id_gen)

            # 2. Create a new PendingRequest with a RED traffic light (Event).
            req = PendingRequest(uid = uid, event = threading.Event())

            # 3. Store the request in our master lookup dictionary
            # with the unique ID as its key.
            self._requests[uid] = req

            # 4. Put this request's ID at the BACK of the waiting line for
            #    this specific OSC route. 
            # Note: This ensures that requests are matched to replies in the
            # order they were registered and supports multiple requests for the
            # same address with the same arguments.
            self._routing_queues[route_key].append(uid)

            # 5. Hand the ticket back to the Sender Thread. (The Sender Thread
            #    will now send the network message and call `req.event.wait()`).
            return req

    def resolve(self, route_key: tuple[Any, ...], payload: Any) -> int | None:
        """
        Called by the LISTENER THREAD when an OSC reply arrives from the network.
        It finds the oldest waiting request for that route and wakes it up.

        It uses the address to find the oldest waiting request for that route.
        """
        with self._lock:
            # Look up the waiting line for this OSC route.
            # NOTE: The return type is either a double-ended queue or None.
            # deque is not an operation.
            queue: deque[int] | None = self._routing_queues.get(route_key)

            # Keep checking the line as long as there are IDs waiting in it.
            while queue:
                # Pull the oldest ID from the FRONT of the line (FIFO).
                uid: int = queue.popleft()

                # Look up the actual PendingRequest object using that ID.
                req: PendingRequest | None = self._requests.get(uid)

                # EDGE CASE CHECK:
                # What if the Sender Thread got tired of waiting (timed out) and
                # already deleted its request via `cleanup()`?
                # If `req` is None, that request was abandoned, so the `while`
                # loop continues to check the next ID in line.
                if req is not None:
                    # 1. Attach the incoming answer data to the request.
                    req.payload = payload

                    # 2. Turn the traffic light GREEN! This wakes up the paused
                    #    Sender Thread so it can read `req.payload`.
                    req.event.set()

                    # 3. Return the matched ID to confirm success.
                    return uid

            # If no active requests were waiting for this route, return None.
            return None

    def cleanup(self, route_key: tuple[Any, ...], uid: int) -> None:
        """
        Called by the SENDER THREAD inside a `finally:` block after it finishes
        waiting (whether it got a reply, timed out, or crashed).
        Ensures no leftover data leaks memory.
        """
        with self._lock:
            # 1. Remove the request from the master dictionary.
            #    Using `.pop(uid, None)` safely does nothing if it's already gone.
            self._requests.pop(uid, None)

            # 2. Check if the double-ended queue still exists for this route.
            queue: deque[int] | None = self._routing_queues.get(route_key)
            if queue:
                try:
                    # If the request timed out before a reply arrived, its ID
                    # is still sitting in the waiting line. Remove it.
                    queue.remove(uid)
                except ValueError:
                    # If `resolve()` already matched this request, it already
                    # popped the ID from the queue, triggering a ValueError.
                    # That's totally normal, so we safely ignore it.
                    pass

                # 3. Memory housekeeping: If the waiting line for this route is
                #    now completely empty, delete the empty line from the dictionary.
                if not queue:
                    del self._routing_queues[route_key]
