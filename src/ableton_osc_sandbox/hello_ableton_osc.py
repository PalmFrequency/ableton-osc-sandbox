import importlib
import subprocess
import sys
import threading
import time
from typing import Any

# =====================================================================
# CORE ENGINE MODULE PROVISIONER
# Auto-manages runtime dependencies cleanly before loop execution
# =====================================================================
REQUIRED_DEPENDENCIES: dict[str, str] = {
    "pythonosc": "python-osc"  # Adjusted key to map the real package folder name
}

def auto_provision_environment():
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

connection_verified = False



# ------------------------------------------------------------------------------------
# Experimental
# ------------------------------------------------------------------------------------
class ThreadSafeDictTrackedElement: # E.g. tracked_element_id = "float"
    def __init__(self, tracked_element_id: str, track_dict: dict[int, Any]) -> None:
        self.tracked_element_id: str = tracked_element_id
        self.track_dict: dict[int, Any] = track_dict
class ThreadSafeDictFunction: # E.g. function = "volume"
    def __init__(self, function_name: str, dict_elem: dict[str, ThreadSafeDictTrackedElement]) -> None:
        self.function_name: str = function_name.strip()
        self.dict_elem: dict[str, ThreadSafeDictTrackedElement] = dict_elem

thread_safe_func_dict: dict[str, ThreadSafeDictFunction] = {}

volume_function: ThreadSafeDictFunction = ThreadSafeDictFunction(
    function_name = "volume",
    dict_elem = {
        "data": ThreadSafeDictTrackedElement(tracked_element_id = "float", track_dict = {}),#E.g. tracked_element_by_track = {0: float, 1: float}
        "tracking": ThreadSafeDictTrackedElement(tracked_element_id = "threading.Event", track_dict = {}), #E.g. tracked_element_by_track = {0: threading.Event(), 1: threading.Event()}
    }
)
thread_safe_func_dict["volume"] = volume_function
volume_tracking: dict[int, threading.Event] = thread_safe_func_dict["volume"].dict_elem["tracking"].track_dict
volume_data: dict[int, float] = thread_safe_func_dict["volume"].dict_elem["data"].track_dict
# E.g. thread_safe_func_dict["volume"].dict_elem["data"].track_dict[0] = 0.5


# Simulated Polling Execution Loop
def poll_track_volume(track_index: int, intervals: int = 5, delay: float = 1.0):
    """
    Polls the volume address of a single track repeatedly over time,
    maintaining strict association and chronological order.
    """
    print(f"⏱️ Starting Polling sequence for Track {track_index + 1} ({intervals} samples)...")
    
    for i in range(intervals):
        start_poll = time.perf_counter()
        
        # Every single call blocks sequentially and returns its explicit payload matches
        volume = query_track_volume_sync(track_index=track_index)
        
        elapsed = time.perf_counter() - start_poll
        if volume is not None:
            print(f" └─ [Sample #{i+1}] Vol: {volume:.2f} | Association: Verified | Latency: {elapsed*1000:.1f}ms")
        else:
            print(f" └─ [Sample #{i+1}] Dropped or timed out.")
            
        time.sleep(delay)


def volume_handler(address, *args):
    # AbletonOSC format: [track_num: int, volume_level: float]
    if len(args) >= 2:
        track_idx = args[0]
        volume_level = args[1]
        
        volume_data[track_idx] = volume_level
        print(f"[Callback] Track {track_idx + 1} Volume Level: {volume_level:.2f}")
        
        # Safely unblock the discrete thread waiting for this specific track index
        if track_idx in volume_tracking:
            volume_tracking[track_idx].set()

def default_handler(address, *args):
    print(f"[Unmapped Address] Received payload on: {address} -> {args}")

# # =====================================================================
# # SYNCHRONIZATION EVENT
# # This allows the main thread to wait securely for callbacks to fire,
# # replacing arbitrary time.sleep() delays with instant wake-ups or timeouts.
# # =====================================================================
# response_event = threading.Event()

# =====================================================================
# CALLBACK HANDLERS
# These instantly unblock the main script by calling response_event.set()
# =====================================================================

# This handler will be triggered when Ableton responds to a 
# /live/test/ping message.
#
# The most reliable way to confirm code-level communication is to send 
# a global ping. AbletonOSC natively supports a /live/test/ping 
# address, which forces Ableton to immediately echo back a reply on 
# your listening port without needing to query a complex state.

# def ping_handler(address, *args):
#     global connection_verified
#     connection_verified = True
#     print("[SUCCESS] Confirmed Connection to Ableton Live! (ping_handler)")
#     print(f"[SUCCESS] Connected! Received ping response from Ableton: {address} -> {args}")
#     response_event.set()  # 🟢 Wake up the main thread immediately

# def tempo_handler(address, *args):
#     global connection_verified
#     connection_verified = True
#     print("[SUCCESS] Confirmed Connection to Ableton Live! (tempo_handler)")
#     print(f"[SUCCESS] Current Project Tempo: {args[0]:.2f} BPM")
#     response_event.set()  # 🟢 Wake up the main thread immediately

# def volume_handler(address, *args):
#     global connection_verified
#     connection_verified = True
#     print("[SUCCESS] Confirmed Connection to Ableton Live! (volume_handler)")
#     # AbletonOSC returns volume as a list  [track_num:int, volume_level:float] (typically 0.0 to 1.0)
#     volume_level = args[1]
#     print(f"[Response] Track 1 Volume Level: {volume_level:.2f}")
#     response_event.set()  # 🟢 Wake up the main thread immediately

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

    # # Catch-all handler for unmapped OSC addresses
    # def default_handler(address, *args):
    #      global connection_verified
    #      connection_verified = True
    #      print("[SUCCESS] Confirmed Connection to Ableton Live! (default handler)")
    #      print(f"[Response] Received unmapped address: {address} -> {args}")
    #      response_event.set()  # 🟢 Wake up the main thread immediately


# =====================================================================
# Set up the local server to listen for Ableton's reply
# and register paths with event handlers through Dispatcher
# =====================================================================
disp = dispatcher.Dispatcher()
disp.map(address = "/live/track/get/volume", handler = volume_handler)
disp.set_default_handler(default_handler)

#disp.map("/live/test/ping", ping_handler)
#disp.map("/live/song/get/tempo", tempo_handler)
#disp.map(address = "/live/api/get/log_level", handler = log_level_handler)
# Catch-all handler to see if Ableton is sending *anything* else (to unmapped path addresses)
#disp.set_default_handler(lambda addr, *args: print(f"\n[SUCCESS] Confirmed Connection to Ableton Live! (default handler)\nReceived unmapped address: {addr} -> {args}"))


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
def query_track_volume_sync(track_index: int, timeout: float = 2.0) -> float | None:
    """
    Encapsulates fire-and-forget OSC messages into a synchronous, 
    timeout-enforced call—mirroring our MultithreadedIO pattern.
    """
    # 1. Initialize a discrete tracking event for this query
    track_event = threading.Event()
    volume_tracking[track_index] = track_event
    
    print(f"Querying current track {track_index + 1} volume level...")
    osc_client.send_message("/live/track/get/volume", [track_index])
    
    # 2. Block the main execution thread securely until the target callback fires
    success: bool = track_event.wait(timeout=timeout)
    
    # 3. Clean up the tracking structure instantly to prevent leaks
    del volume_tracking[track_index]
    
    if success:
        return volume_data.get(track_index)
    else:
        print(f"[-] [TIMEOUT] Track {track_index + 1} failed to respond within {timeout}s.")
        return None

# =====================================================================
# Main Sequence Operations Execution
# =====================================================================
try:
    # Query track 1 sequentially
    vol1: float | None = query_track_volume_sync(track_index=0)
    
    # Query track 2 sequentially 
    vol2: float | None = query_track_volume_sync(track_index=1)
    
    # Example Set Operations
    print("\nModifying levels...")
    osc_client.send_message("/live/track/set/volume", [0, 0.5])
    osc_client.send_message("/live/track/set/volume", [1, 0.9])
    time.sleep(0.1)  # DAW processing pause for non-echo commands
    
    print("\nRe-verifying track states:")
    final_vol1: float | None = query_track_volume_sync(track_index=0)
    final_vol2: float | None = query_track_volume_sync(track_index=1)

finally:
    print("\nCleaning up server contexts...")
    server.shutdown()
    server.server_close()
    print("Server shut down successfully.")


# """
# #print("Sending Ping to Ableton...")  ---NOT WORKING
# #response_event.clear() # 🔴 Reset the event light to red
# #osc_client.send_message("/live/test/ping", ["Python Check"])

# # Request current log level of ableton-osc
# # log is located at C:\Users\dev\Documents\Ableton\User Library\Remote Scripts\AbletonOSC\logs
# print("\nQuerying current ableton-osc log level ...") 
# response_event.clear() # 🔴 Reset the event light to red
# osc_client.send_message(address = "/live/api/get/log_level", value = [])
# # Wait max 5 seconds for the log_level_handler to set the event to green
# if not response_event.wait(timeout=5.0):
#     print("[FAILURE] Log level query timed out.")
#     print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")
#     server.shutdown()
#     sys.exit(1)

# #print("Verifying link by requesting project tempo...")
# #response_event.clear() # 🔴 Reset the event light to red
# #osc_client.send_message("/live/song/get/tempo", [])

# # Request current volume level of first track
# print("\nQuerying current track 1 (index: 0) volume level ...")
# response_event.clear() # 🔴 Reset the event light to red
# osc_client.send_message(address = "/live/track/get/volume", value = [0])

# # Request current volume level of second track
# print("\nQuerying current track 2 (index: 1) volume level ...")
# response_event.clear() # 🔴 Reset the event light to red
# osc_client.send_message(address = "/live/track/get/volume", value = [1])

# # Set volume level of first track
# target_volume_level = 0.50
# print(f"\nSetting track 1 (index: 0) volume to {target_volume_level*100:.0f}% depth ({target_volume_level})...")
# # Value must be a float in a list ([])
# osc_client.send_message(address = "/live/track/set/volume", value=[0, target_volume_level])
# # AbletonOSC 'set' commands do not echo a reply, so we use a tiny 0.1s pause 
# # just to let the DAW process it before querying the new state.
# time.sleep(0.1)

# # Set volume level of second track
# target_volume_level = 1.00
# print(f"\nSetting track 2 (index: 1) volume to {target_volume_level*100:.0f}% depth ({target_volume_level})...")
# # Value must be a float in a list ([])
# osc_client.send_message(address = "/live/track/set/volume", value=[1, target_volume_level])
# # AbletonOSC 'set' commands do not echo a reply, so we use a tiny 0.1s pause 
# # just to let the DAW process it before querying the new state.
# time.sleep(0.1)

# # Re-request current volume level of first track
# print("\nRe-querying current track 1 (index: 0) volume level ...")
# response_event.clear() # 🔴 Reset the event light to red
# osc_client.send_message(address = "/live/track/get/volume", value = [0])

# # Re-request current volume level of second track
# print("\nRe-querying current track 2 (index: 1) volume level ...")
# response_event.clear() # 🔴 Reset the event light to red
# osc_client.send_message(address = "/live/track/get/volume", value = [1])

# if not connection_verified:
#     print("[FAILURE] No response from Ableton. Not recognizing response payload.")
#     print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")

# # Clean up
# server.shutdown()
# server.server_close()
# print("Server shut down successfully.")
# """