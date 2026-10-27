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

ping_received = False
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
    global ping_received
    ping_received = True
    print(f"\n[SUCCESS] Connected! Received response from Ableton: {address} -> {args}")

# =====================================================================
# CALLBACK HANDLER
# =====================================================================
def tempo_handler(address, *args):
    global connection_verified
    connection_verified = True
    print("\n[SUCCESS] Confirmed Connection to Ableton Live!")
    print(f"-> Current Project Tempo: {args[0]:.2f} BPM")

# =====================================================================
# CALLBACK HANDLER
# callback function to listen for Ableton OSC responses
# =====================================================================
def volume_handler(address, *args):
    """Callback function executed when Ableton replies with the volume."""
    # AbletonOSC returns volume as a float parameter (typically 0.0 to 1.0)
    volume_level = args[0]
    print(f"\n[Response] Master Volume Level: {volume_level:.2f}")

# =====================================================================
# Set up the local server to listen for Ableton's reply
# =====================================================================
disp = dispatcher.Dispatcher()
#disp.map("/live/test/ping", ping_handler)
disp.map("/live/song/get/tempo", tempo_handler)
#disp.map("/live/master/get/volume", volume_handler)

# Catch-all handler to see if Ableton is sending *anything* else
disp.set_default_handler(lambda addr, *args: print(f"[Traffic Alert] Received unmapped address: {addr} -> {args}"))


server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", LOCAL_PORT), disp)
threading.Thread(target=server.serve_forever, daemon=True).start()
print(f"Listening for Ableton replies on port {LOCAL_PORT}...")

# =====================================================================
#  Set up the client to send commands to Ableton.
#  Fire valid requests with Ableton running
# =====================================================================
osc_client = udp_client.SimpleUDPClient(ABLETON_IP, ABLETON_PORT)

#print("Sending Ping to Ableton...")
#osc_client.send_message("/live/test/ping", ["Python Check"])

print("Verifying link by requesting project tempo...")
osc_client.send_message("/live/song/get/tempo", [])

# Request current volume leve
#osc_client.send_message("/live/master/get/volume", [])

# Keep the script running for 5 seconds to receive the background data
time.sleep(5.0)

if not connection_verified:
    #print("\n[FAILURE] No response from Ableton. Python is shouting into the void.")
    #print("-> Verify Ableton is running and AbletonOSC is selected under Link/MIDI Preferences.")
    print("\n[FAILURE] Still no recognized response payload.")

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