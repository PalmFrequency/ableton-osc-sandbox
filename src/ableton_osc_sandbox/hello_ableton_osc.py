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
# CALLBACK HANDLER
# This handler will be triggered when Ableton responds to a 
# /live/test/ping message.
#
# The most reliable way to confirm code-level communication is to send 
# a global ping. AbletonOSC natively supports a /live/test/ping 
# address, which forces Ableton to immediately echo back a reply on 
# your listening port without needing to query a complex state.
# =====================================================================
def ping_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("\n[SUCCESS] Confirmed Connection to Ableton Live! (ping_handler)")
    print(f"\n[SUCCESS] Connected! Received ping response from Ableton: {address} -> {args}")

# =====================================================================
# CALLBACK HANDLER
# =====================================================================
def tempo_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("\n[SUCCESS] Confirmed Connection to Ableton Live! (tempo_handler)")
    print(f"-> Current Project Tempo: {args[0]:.2f} BPM")

# =====================================================================
# CALLBACK HANDLER
# Callback function executed when Ableton replies with the volume.
#
# args[0] contains the float volume level (0.0 to 1.0)
# =====================================================================
def volume_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("\n[SUCCESS] Confirmed Connection to Ableton Live! (volume_handler)")
    # AbletonOSC returns volume as a list  [track_num:int, volume_level:float] (typically 0.0 to 1.0)
    volume_level = args[1]
    print(f"\n[Response] Track 1 Volume Level: {volume_level:.2f}")

# =====================================================================
# Set up the local server to listen for Ableton's reply
# and map paths with Dispatcher
# =====================================================================
disp = dispatcher.Dispatcher()
disp.map("/live/test/ping", ping_handler)
disp.map("/live/song/get/tempo", tempo_handler)
disp.map("/live/track/get/volume", volume_handler)
# Catch-all handler to see if Ableton is sending *anything* else (to unmapped path addresses)
disp.set_default_handler(lambda addr, *args: print(f"\n[SUCCESS] Confirmed Connection to Ableton Live! (catch-all handler)\nReceived unmapped address: {addr} -> {args}"))

server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", LOCAL_PORT), disp)
threading.Thread(target=server.serve_forever, daemon=True).start()
print(f"Listening for Ableton replies on port {LOCAL_PORT}...")

# =====================================================================
#  Initialize client to send commands to Ableton.
#  Fire valid requests with Ableton running
# =====================================================================
osc_client = udp_client.SimpleUDPClient(ABLETON_IP, ABLETON_PORT)

#print("Sending Ping to Ableton...")  ---NOT WORKING
#osc_client.send_message("/live/test/ping", ["Python Check"])

#print("Verifying link by requesting project tempo...")
#osc_client.send_message("/live/song/get/tempo", [])

# Request current volume level of first track
print("Querying current track 1 (index: 0) volume level ...")
osc_client.send_message("/live/track/get/volume", [0])
# Keep the script running for 5 seconds to receive the background data
time.sleep(5.0)

# Set volume level of first track
target_volume_level = 0.75
print(f"Setting track 1 (index: 0) volume to {target_volume_level*100:.0f}% depth ({target_volume_level})...")
# Value must be a float in a list ([])
osc_client.send_message("/live/track/set/volume", [0, target_volume_level])
# Keep the script running for 5 seconds to send the background data
time.sleep(5.0)

# Request current volume level of first track
print("Re-querying current track 1 (index: 0) volume level ...")
osc_client.send_message("/live/track/get/volume", [0])
# Keep the script running for 5 seconds to receive the background data
time.sleep(5.0)

if not connection_verified:
    print("\n[FAILURE] No response from Ableton. Not recognizing response payload.")
    print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")

# Clean up
server.shutdown()
server.server_close()
print("Server shut down successfully.")


# 1. Set the volume to 0%.
#print("Setting master volume to 0%...")
#osc_client.send_message("/live/master/volume", [0])

# 2. Set the volume to 100%.
#print("Setting master volume to 100%...")
#osc_client.send_message("/live/master/volume", [1])