import importlib
import subprocess
import sys
import threading
import time

# =====================================================================
# CORE ENGINE MODULE PROVISIONER
# Auto-manages runtime dependencies cleanly before loop execution
# =====================================================================
REQUIRED_DEPENDENCIES = {
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

# =====================================================================
# SYNCHRONIZATION EVENT
# This allows the main thread to wait securely for callbacks to fire,
# replacing arbitrary time.sleep() delays with instant wake-ups or timeouts.
# =====================================================================
response_event = threading.Event()

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

def ping_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("[SUCCESS] Confirmed Connection to Ableton Live! (ping_handler)")
    print(f"[SUCCESS] Connected! Received ping response from Ableton: {address} -> {args}")
    response_event.set()  # 🟢 Wake up the main thread immediately

def tempo_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("[SUCCESS] Confirmed Connection to Ableton Live! (tempo_handler)")
    print(f"[SUCCESS] Current Project Tempo: {args[0]:.2f} BPM")
    response_event.set()  # 🟢 Wake up the main thread immediately

def volume_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("[SUCCESS] Confirmed Connection to Ableton Live! (volume_handler)")
    # AbletonOSC returns volume as a list  [track_num:int, volume_level:float] (typically 0.0 to 1.0)
    volume_level = args[1]
    print(f"[Response] Track 1 Volume Level: {volume_level:.2f}")
    response_event.set()  # 🟢 Wake up the main thread immediately

# default log_level is 'info'. Other options are 'debug', 'warning', 'error' and 'critical'.
# log is located at C:\Users\dev\Documents\Ableton\User Library\Remote Scripts\AbletonOSC\logs
def log_level_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("[SUCCESS] Confirmed Connection to Ableton Live! (log_level_handler)")
    # AbletonOSC returns log level as a list  [log_level:int] (typically 0 to 3)
    log_level = args[0]
    print(f"[Response] ableton-osc Log Level: {log_level}")
    response_event.set()  # 🟢 Wake up the main thread immediately

# Catch-all handler for unmapped OSC addresses
def default_handler(address, *args):
     global connection_verified
     connection_verified = True
     print("[SUCCESS] Confirmed Connection to Ableton Live! (default handler)")
     print(f"[Response] Received unmapped address: {address} -> {args}")
     response_event.set()  # 🟢 Wake up the main thread immediately


# =====================================================================
# Set up the local server to listen for Ableton's reply
# and register paths with event handlers through Dispatcher
# =====================================================================
disp = dispatcher.Dispatcher()
#disp.map("/live/test/ping", ping_handler)
#disp.map("/live/song/get/tempo", tempo_handler)
#disp.map("/live/track/get/volume", volume_handler)
#disp.map("/live/api/get/log_level", log_level_handler)
# Catch-all handler to see if Ableton is sending *anything* else (to unmapped path addresses)
#disp.set_default_handler(lambda addr, *args: print(f"\n[SUCCESS] Confirmed Connection to Ableton Live! (default handler)\nReceived unmapped address: {addr} -> {args}"))
disp.set_default_handler(default_handler)

server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", LOCAL_PORT), disp)
threading.Thread(target=server.serve_forever, daemon=True).start()
print(f"\nListening for Ableton replies on port {LOCAL_PORT}...\n")

# =====================================================================
#  Initialize client to send commands to Ableton.
#  Fire valid requests with Ableton running
# =====================================================================
osc_client = udp_client.SimpleUDPClient(ABLETON_IP, ABLETON_PORT)

#print("Sending Ping to Ableton...")  ---NOT WORKING
#response_event.clear() # 🔴 Reset the event light to red
#osc_client.send_message("/live/test/ping", ["Python Check"])

# Request current log level of ableton-osc
# log is located at C:\Users\dev\Documents\Ableton\User Library\Remote Scripts\AbletonOSC\logs
print("\nQuerying current ableton-osc log level ...") 
response_event.clear() # 🔴 Reset the event light to red
osc_client.send_message("/live/api/get/log_level", [])
# Wait max 5 seconds for the log_level_handler to set the event to green
if not response_event.wait(timeout=5.0):
    print("[FAILURE] Log level query timed out.")
    print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")
    server.shutdown()
    sys.exit(1)

#print("Verifying link by requesting project tempo...")
#response_event.clear() # 🔴 Reset the event light to red
#osc_client.send_message("/live/song/get/tempo", [])

# Request current volume level of first track
print("\nQuerying current track 1 (index: 0) volume level ...")
response_event.clear() # 🔴 Reset the event light to red
osc_client.send_message("/live/track/get/volume", [0])
# Wait max 5 seconds for the volume_handler to set the event to green
if not response_event.wait(timeout=5.0):
    print("[FAILURE] Volume query timed out.")
    print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")
    server.shutdown()
    sys.exit(1)

# Set volume level of first track
target_volume_level = 0.75
print(f"\nSetting track 1 (index: 0) volume to {target_volume_level*100:.0f}% depth ({target_volume_level})...")
# Value must be a float in a list ([])
osc_client.send_message("/live/track/set/volume", [0, target_volume_level])
# AbletonOSC 'set' commands do not echo a reply, so we use a tiny 0.1s pause 
# just to let the DAW process it before querying the new state.
time.sleep(0.1)

# Request current volume level of first track
print("\nRe-querying current track 1 (index: 0) volume level ...")
response_event.clear() # 🔴 Reset the event light to red
osc_client.send_message("/live/track/get/volume", [0])
if not response_event.wait(timeout=5.0):
    print("[FAILURE] Second volume query timed out.")
    print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")
    server.shutdown()
    sys.exit(1)


if not connection_verified:
    print("[FAILURE] No response from Ableton. Not recognizing response payload.")
    print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")

# Clean up
server.shutdown()
server.server_close()
print("Server shut down successfully.")