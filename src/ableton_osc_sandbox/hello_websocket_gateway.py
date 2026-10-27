import importlib
import json
import subprocess
import sys

# =====================================================================
# CORE ENGINE MODULE PROVISIONER
# Auto-manages runtime dependencies cleanly before loop execution
# =====================================================================
REQUIRED_DEPENDENCIES = {
    "websockets": "websockets",
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

import asyncio

import websockets
from pythonosc.udp_client import SimpleUDPClient  # Fixed namespace reference path here

# Infrastructure routing constraints
ABLETON_IP = "127.0.0.1"
ABLETON_PORT = 9000
WS_HOST = "127.0.0.1"
WS_PORT = 8765

# Instantiated outbound UDP transmission pipeline
osc_client = SimpleUDPClient(ABLETON_IP, ABLETON_PORT)


async def handle_marimo_transaction(websocket):
    print("📡 Successful incoming connection recognized from UI interface!")
    try:
        # Listen continuously for incoming messages from the browser
        async for frame_message in websocket:
            try:
                # Parse the incoming JSON data
                payload = json.loads(frame_message)
                address_path = payload.get("address", "/live/master/volume")
                parameter_value = float(payload.get("value", 0.5))

                print(f"🎛️ Routing downstream: {address_path} ➔ {parameter_value}")

                # Forward the command to Ableton via UDP
                # Note: AbletonOSC expects parameter_value as a list (e.g., [124.0]) or empty list []
                osc_client.send_message(address_path, parameter_value)

            except (ValueError, TypeError) as parse_error:
                print(f"⚠️ Transaction validation error dropped: {parse_error}")

    except websockets.exceptions.ConnectionClosedOK:
        print("🔌 UI client stream connection terminated cleanly.")


async def main():
    print(f"🚀 PalmFrequency Gateway active at ws://{WS_HOST}:{WS_PORT}")
    print("Waiting for browser/client connections...")
    # Start the WebSocket server and hold the thread infinitely
    #async with websockets.serve(handle_marimo_transaction, WS_HOST, WS_PORT):
    #async with websockets.serve(handler=handle_marimo_transaction, host="localhost", port=8765):
    async with websockets.serve(handle_marimo_transaction,WS_HOST,WS_PORT) as server:
        await asyncio.Future()  # Infinite thread hold


if __name__ == "__main__":
    asyncio.run(main())