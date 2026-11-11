import importlib
import subprocess
import sys
import threading
import time
from typing import Any

# TODO: Place globals in a Singleton; Implement subscribe/listen pattern with AbletonOSC; 
# Understand all patterns (i.e. all request and response arg types X values X order X number)
# And make generic handlers and trackers for them

# Summary of Benefits
#
# • Zero ID Reuse: itertools.count(1) ensures every request gets a lifetime-unique integer ID (1, 2, 3...), preventing cross-talk between timed-out and active calls.
# • No Global Payload Collisions: Storing payload directly on the PendingRequest instance means concurrent threads never overwrite each other's return values.
# • Leak-Free: The finally block ensures both _requests and _routing_queues purge empty entries immediately after completion or timeout.
# • Generic Foundation: Because query_osc_sync takes address, send_args, and match_args, it directly supports your # TODO goal of building generic handlers for all AbletonOSC argument patterns.
#
# Would you like to expand this OSCRequestTracker into the Singleton mentioned in your TODO comments, or adapt it to support AbletonOSC's /start_listen subscription pattern next?


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



# ------------------------------------------------------------------------------------
# Experimental
# ------------------------------------------------------------------------------------
global_event_tracking: dict[Any, threading.Event] = dict[Any, threading.Event]()
volume_data: dict[Any, float] = dict[Any, float]()
test_data: str | None = None



# # Simulated Polling Execution Loop
# def poll_track_volume(track_index: int, intervals: int = 5, delay: float = 1.0) -> None:
#     """
#     Polls the volume address of a single track repeatedly over time,
#     maintaining strict association and chronological order.
#     """
#     print(f"⏱️ Starting Polling sequence for Track {track_index + 1} ({intervals} samples)...")
    
#     for i in range(intervals):
#         start_poll = time.perf_counter()
        
#         # Every single call blocks sequentially and returns its explicit payload matches
#         volume: float | None = query_track_volume_sync(track_index=track_index)
        
#         elapsed: float = time.perf_counter() - start_poll
#         if volume is not None:
#             print(f" └─ [Sample #{i+1}] Vol: {volume:.2f} | Association: Verified | Latency: {elapsed*1000:.1f}ms")
#         else:
#             print(f" └─ [Sample #{i+1}] Dropped or timed out.")
            
#         time.sleep(delay)


def volume_handler(address, *args) -> None:
    # AbletonOSC format: [track_num: int, volume_level: float]
    if len(args) >= 2:
        track_idx = args[0]
        volume_level = args[1]
        
        volume_data[track_idx] = volume_level
        print(f"[Callback] Track {track_idx + 1} Volume Level: {volume_level:.2f}")
        
        # Safely unblock the discrete thread waiting for this specific track index
        request_id: str = address + " " + str(object = track_idx)
        if request_id in global_event_tracking:
            global_event_tracking[request_id].set()

def test_handler(address, *args) -> None:
    # AbletonOSC format: [status: str]
    global test_data
    test_data = args[0]
    print(f"[Callback] Test response received: {address} -> {args}")
    
    request_id: str = address + " "
    if request_id in global_event_tracking:
        global_event_tracking[request_id].set()



def default_handler(address, *args) -> None:
    print(f"[Unmapped Address] Received payload on: {address} -> {args}")


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



# =====================================================================
# Set up the local server to listen for Ableton's reply
# and register paths with event handlers through Dispatcher
# =====================================================================
disp = dispatcher.Dispatcher()
disp.map(address = "/live/track/get/volume", handler = volume_handler)
disp.map(address = "/live/test", handler = test_handler)
disp.set_default_handler(default_handler)

#disp.map("/live/song/get/tempo", tempo_handler)
#disp.map(address = "/live/api/get/log_level", handler = log_level_handler)
# Catch-all handler to see if Ableton is sending *anything* else (to unmapped path addresses)

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
def query_test_sync_global(timeout: float = 2.0) -> tuple[str, str | None]:
    """
    Encapsulates fire-and-forget OSC messages into a synchronous, 
    timeout-enforced call—mirroring our MultithreadedIO pattern.
    """
    address = "/live/test"

    # 1. Initialize a discrete tracking event for this query and register it globally
    request_id: str = address + " "
    track_event = threading.Event()
    global_event_tracking[request_id] = track_event
    
    print("Querying Ableton test response...")
    osc_client.send_message(address = address, value = [])
    
    # 2. Block the main execution thread securely until the target callback fires or timeouts
    success: bool = track_event.wait(timeout = timeout)
    
    # 3. Clean up the tracking structure instantly to prevent leaks
    del global_event_tracking[request_id]
    
    if success:
        return request_id, test_data
    else:
        print(f"[-] [TIMEOUT] Test failed to respond within {timeout}s.")
        return request_id, None
    
def query_track_volume_sync_global(track_index: int, timeout: float = 2.0) -> tuple[str, float | None]:
    """
    Encapsulates fire-and-forget OSC messages into a synchronous, 
    timeout-enforced call—mirroring our MultithreadedIO pattern.
    """
    address = "/live/track/get/volume"

    # 1. Initialize a discrete tracking event for this query and register it globally
    request_id: str = address + " " + str(object = track_index)
    track_event = threading.Event()
    global_event_tracking[request_id] = track_event
    
    print(f"Querying current track {track_index + 1} volume level...")
    osc_client.send_message(address = address, value = [track_index])
    
    # 2. Block the main execution thread securely until the target callback fires or timeouts
    success: bool = track_event.wait(timeout = timeout)
    
    # 3. Clean up the tracking structure instantly to prevent leaks
    del global_event_tracking[request_id]
    
    if success:
        return request_id, volume_data.get(track_index)
    else:
        print(f"[-] [TIMEOUT] Track {track_index + 1} failed to respond within {timeout}s.")
        return request_id, None



# =====================================================================
# Main Sequence Operations Execution
# =====================================================================
try:
    # Ping Ableton via AbletonOSC sequentially (Note: Returns a 2-element tuple)
    request_id0, test_response = query_test_sync_global()

    # Query track 1 sequentially (Note: Returns a 2-element tuple)
    request_id1, vol1 = query_track_volume_sync_global(track_index = 0)
    
    # Query track 2 sequentially (Note: Returns a 2-element tuple)
    request_id2, vol2 = query_track_volume_sync_global(track_index = 1)
    
    # Example Set Operations (no call backs)
    print("\nModifying levels (Note: No callbacks)...")
    osc_client.send_message(address = "/live/track/set/volume", value = [0, 0.5])
    osc_client.send_message(address = "/live/track/set/volume", value = [1, 0.9])
    time.sleep(0.1)  # DAW processing pause for non-echo commands
    
    print("\nRe-verifying track states (Note: Returns a 2-element tuple):")
    request_id3, final_vol1 = query_track_volume_sync_global(track_index = 0)
    request_id4, final_vol2 = query_track_volume_sync_global(track_index = 1)

finally:
    print("\nCleaning up server contexts...")
    server.shutdown()
    server.server_close()
    print("Server shut down successfully.")