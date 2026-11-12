import importlib
import subprocess
import sys
import threading
import time
from typing import Any

import osc_request_tracker

# from .osc_request_tracker import (
#     OSCRequestTracker,  # instructs ty to look in current folder
#     PendingRequest,
# )

# TODO: Place globals in a Singleton; Implement subscribe/listen pattern with AbletonOSC; 
# Understand all patterns (i.e. all request and response arg types X values X order X number)
# And make generic handlers and trackers for them

# Summary of Benefits
#
# • Zero ID Reuse: itertools.count(1) ensures every request gets a lifetime-unique integer 
# ID (1, 2, 3...), preventing cross-talk between timed-out and active calls.
# • No Global Payload Collisions: Storing payload directly on the PendingRequest instance 
# means concurrent threads never overwrite each other's return values.
# • Leak-Free: The finally block ensures both _requests and _routing_queues purge empty 
# entries immediately after completion or timeout.
# • Generic Foundation: Because query_osc_sync takes address, send_args, and match_args, 
# it directly supports your # TODO goal of building generic handlers for all AbletonOSC argument patterns.
#
# Would you like to expand this OSCRequestTracker into the Singleton mentioned in your TODO 
# comments, or adapt it to support AbletonOSC's /start_listen subscription pattern next?


# =====================================================================
# CORE ENGINE MODULE PROVISIONER
# Auto-manages runtime dependencies cleanly before loop execution
# =====================================================================
REQUIRED_DEPENDENCIES: dict[str, str] = {
    "pythonosc": "python-osc"  # Adjusted key to map the real package folder name
}

def auto_provision_environment() -> None:
    for module_name, package_name in REQUIRED_DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            print(f"📦 Environment missing '{package_name}'. Auto-provisioning...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                print(f"✅ Successfully provisioned {package_name}")
            except Exception as error:
                print(f"❌ Structural setup failure for {package_name}: {error}")
                sys.exit(1)


# Ensure packages are locally available before proceeding to network loops
auto_provision_environment()

from pythonosc import dispatcher, osc_server, udp_client

ABLETON_IP = "127.0.0.1"
# AbletonOSC listens on port 11000 and sends replies to 11001 locally
ABLETON_PORT = 11000
LOCAL_PORT = 11001


tracker = osc_request_tracker.OSCRequestTracker()



# =====================================================================
# CALLBACK HANDLERS
# These instantly unblock the main script by calling response_event.set()
# =====================================================================

# # default log_level is 'info'. Other options are 'debug', 'warning', 'error' and 'critical'.
# # log is located at C:\Users\dev\Documents\Ableton\User Library\Remote Scripts\AbletonOSC\logs
# def log_level_handler(address, *args):
#     global connection_verified
#     connection_verified = True
#     print("[SUCCESS] Confirmed Connection to Ableton Live! (log_level_handler)")
#     # AbletonOSC returns log level as a list  [log_level:int] (typically 0 to 3)
#     log_level = args[0]
#     print(f"[Response] ableton-osc Log Level: {log_level}")
#     response_event.set()  # 🟢 Wake up the main thread immediately

def volume_handler(address: str, *args: Any) -> None:
    if len(args) >= 2:
        track_idx: int = args[0]
        volume_level: float = args[1]
        route_key: tuple[str, Any] = (address, track_idx)
        matched_uid: int | None = tracker.resolve(route_key, payload = volume_level)
        print(f"[Callback | Req #{matched_uid}] Track {track_idx + 1} Volume: {volume_level:.2f}")

def test_handler(address: str, *args: Any) -> None:
    status: Any | None = args[0] if args else None
    route_key: tuple[str, ...] = (address,)
    matched_uid: int | None = tracker.resolve(route_key, payload = status)
    print(f"[Callback | Req #{matched_uid}] Test response: {status}")

def default_handler(address: str, *args: Any) -> None:
    print(f"[Unmapped Address] Received payload on: {address} -> {args}")


# =====================================================================
# Set up the local server to listen for Ableton's reply
# and register paths with event handlers through Dispatcher
# =====================================================================
disp = dispatcher.Dispatcher()
disp.map(address = "/live/track/get/volume", handler = volume_handler)
disp.map(address = "/live/test", handler = test_handler)
disp.set_default_handler(default_handler)

server = osc_server.ThreadingOSCUDPServer(server_address = ("127.0.0.1", LOCAL_PORT), dispatcher = disp)
server_thread: threading.Thread = threading.Thread(target = server.serve_forever, daemon = True)
server_thread.start()
print(f"\nListening for Ableton replies on port {LOCAL_PORT}...\n")


# =====================================================================
#  Initialize client to send commands to Ableton.
#  Fire valid requests with Ableton running
# =====================================================================
osc_client = udp_client.SimpleUDPClient(address = ABLETON_IP, port = ABLETON_PORT)


# =====================================================================
# Synchronous Execution Wrapper Pattern
# =====================================================================
"""
Using try...finally guarantees tracker.cleanup() executes even if the script 
is interrupted or throws an exception:
"""
def query_osc_sync(
    address: str, 
    send_args: list[Any], 
    match_args: tuple[Any, ...], 
    timeout: float = 2.0
) -> tuple[int, Any | None]:
    """
    Generic synchronous wrapper for any AbletonOSC query.
    :param match_args: The leading arguments AbletonOSC echoes back to identify the target.

    Note: tuple[Any, ...] tells the type checker that the tuple can have any number of 
    elements (0, 1, 2, or more).

    In the code example, route_key varies in length depending on the AbletonOSC endpoint:
    • For /live/test, route_key has 1 element: ("/live/test",)
    • For /live/track/get/volume, route_key has 2 elements: ("/live/track/get/volume", 0)
    • For a clip property like /live/clip/get/name, route_key would have 3 elements: 
    ("/live/clip/get/name", 0, 1)
    
    Because dictionaries require hashable (immutable) keys, a tuple is required instead of 
    a list, and tuple[Any, ...] allows that tuple key to hold any number of identifying 
    arguments. (Note: ... only works with a single type before it—you cannot write 
    tuple[str, Any, ...]).
    """
    # A route key combines the OSC address with its identifying arguments.
    route_key: tuple[str, *tuple[Any, ...]] = (address, *match_args)
    # Lifecycle Example (1-6)
    # 1. Sender Thread calls req = tracker.register(('/get/status',)) to get 
    # a ticket.
    req: PendingRequest = tracker.register(route_key)

    try:
        # 2. Sender Thread sends the actual OSC network message.
        osc_client.send_message(address = address, value = send_args)
        # 3. Sender Thread calls req.event.wait(timeout=2.0). It freezes here,
        # using zero CPU, waiting for the green light. 
        # (i.e. event.wait() -> ***RED LIGHT***)
        success: bool = req.event.wait(timeout = timeout)
        # 4. Listener Thread (running in the background) receives an OSC message
        # from the network on /get/status with data "OK".
        # 5. Listener Thread calls tracker.resolve(('/get/status',), "OK"). This
        # puts "OK" into req.payload and flips req.event to green.
        # (i.e. event.set() -> ***GREEN LIGHT***)
        # 6. Sender Thread immediately wakes up, reads req.payload ("OK"), and
        # calls tracker.cleanup(...) to tidy up memory.
        return req.uid, (req.payload if success else None)
    finally:
        # Always runs—prevents memory leaks on timeout or exception
        tracker.cleanup(route_key, req.uid)


# =====================================================================
# Main Sequence Operations Execution
# =====================================================================
try:
    # Ping Ableton (sends [], expects reply matching ("/live/test",))
    req_id0, test_response = query_osc_sync(address = "/live/test", 
                                            send_args = [], match_args = ())

    # Query Track 1 (sends, expects reply matching ("/live/track/get/volume", 0))
    req_id1, vol1 = query_osc_sync(address = "/live/track/get/volume", 
                                   send_args = [0], match_args = (0,))

    # Query Track 2 (sends, expects reply matching ("/live/track/get/volume", 1))
    req_id2, vol2 = query_osc_sync(address = "/live/track/get/volume", 
                                   send_args = [1], match_args = (1,))
    
    # Example Set Operations (no call backs)
    print("\nModifying levels (Note: No callbacks)...")
    osc_client.send_message(address = "/live/track/set/volume", value = [0, 0.5])
    osc_client.send_message(address = "/live/track/set/volume", value = [1, 0.9])
    time.sleep(0.1)  # DAW processing pause for non-echo commands
    
    print("\nRe-verifying track states:")
    req_id3, final_vol1 = query_osc_sync(address = "/live/track/get/volume", 
                                         send_args = [0], match_args = (0,))
    req_id4, final_vol2 = query_osc_sync(address = "/live/track/get/volume", send_args = [1], match_args = (1,))

finally:
    print("\nCleaning up server contexts...")
    server.shutdown()
    server.server_close()
    print("Server shut down successfully.")