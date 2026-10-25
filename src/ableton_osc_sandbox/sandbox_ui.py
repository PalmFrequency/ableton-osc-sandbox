import marimo

__generated_with = "0.25.2"
app = marimo.App()


@app.cell
def _():
    import asyncio
    import json
    import sys

    import marimo as mo
    import websockets

    print(f'Python {sys.version} on {sys.platform}')

    # The local routing URL to your gateway
    GATEWAY_URL = "ws://127.0.0.1:8765"

    header = mo.md(
        """
        # 🌴 PalmFrequency
        ## Ableton Live Remote Canvas Control (Phase 1)

        An open-source, non-commercial playground designed to share music 
        production workflows with future learners and collaborative creators.
        """
    )

    # Performance Sliders
    master_volume_slider = mo.ui.slider(
        start=0.0,
        stop=1.0,
        step=0.01,
        value=0.5,
        label="🎛️ Master Track Volume"
    )

    track_1_pan_slider = mo.ui.slider(
        start=-1.0,
        stop=1.0,
        step=0.02,
        value=0.0,
        label="🎚️ Track 1 Panning (L/R)"
    )

    strips = mo.md(f"### Live Performance Strips\n\n{master_volume_slider}\n\n{track_1_pan_slider}")

    #mo.vstack([header, strips])
    # We must output the visual stack so it displays on your canvas canvas
    canvas_output = mo.vstack([header, strips])
    return (
        GATEWAY_URL,
        asyncio,
        canvas_output,
        json,
        master_volume_slider,
        mo,
        track_1_pan_slider,
        websockets,
    )


@app.cell
def initialize_state(mo):
    # FIX: Initialize the state tracker here so it doesn't clear out on slider movement
    prev_state, set_prev_state = mo.state({})
    return prev_state, set_prev_state


@app.cell
def handle_slider_changes(
    GATEWAY_URL,
    asyncio,
    json,
    master_volume_slider,
    prev_state,
    set_prev_state,
    track_1_pan_slider,
    websockets,
):
    # Bundle the current values into a dict
    current_state = {
        "/live/master/volume": master_volume_slider.value,
        "/live/track/0/pan": track_1_pan_slider.value
    }

    print(current_state)  # --------------TONY DEBUG--------------

    async def send_osc_update():
        print("entered function")  # --------------TONY DEBUG--------------
        for address, value in current_state.items():
            print("entered loop")  # --------------TONY DEBUG--------------

            # Reads the true previous state persistently now
            if prev_state().get(address) != value:
                try:
                    print("entered try block")  # --------------TONY DEBUG--------------
                    async with websockets.connect(GATEWAY_URL) as ws:
                        packet = json.dumps({"address": address, "value": value})
                        await ws.send(packet)
                except Exception as e:
                    print(f"entered exception: {e}")  # --------------TONY DEBUG--------------

        # Update the state tracker
        set_prev_state(current_state)

    # Execute the async send
    asyncio.create_task(send_osc_update())
    return


@app.cell
def _(canvas_output):
    # This cell simply renders your layout block onto the page UI
    canvas_output
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
