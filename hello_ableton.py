import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from pythonosc.udp_client import SimpleUDPClient

    # Initialize OSC client pointing to AbletonOSC default port 11000
    # http://localhost:2718/
    client = SimpleUDPClient("127.0.0.1", 11000)

    # Create reactive UI elements
    play_btn = mo.ui.run_button(label="▶ Play")
    stop_btn = mo.ui.run_button(label="⏹ Stop")
    tempo_slider = mo.ui.slider(
        start=60.0, 
        stop=180.0, 
        step=1.0, 
        value=124.0, 
        label="Tempo (BPM)"
    )

    # Display the controls together
    mo.vstack([
        mo.md("### PalmFrequency Ableton Controller"),
        mo.hstack([play_btn, stop_btn]),
        tempo_slider
    ])
    return client, mo, play_btn, stop_btn, tempo_slider


@app.cell
def _(client, mo, play_btn, stop_btn, tempo_slider):
    # Trigger transport playback or stop when buttons are clicked
    if play_btn.value:
        client.send_message("/live/song/start_playing", [])

    if stop_btn.value:
        client.send_message("/live/song/stop_playing", [])

    # Reactively update Ableton's tempo whenever the slider moves
    client.send_message("/live/song/set/tempo", [float(tempo_slider.value)])

    mo.md(f"*Current target tempo:* **{tempo_slider.value} BPM**")
    return


@app.cell
def _(client, mo):
    import socket
    from pythonosc.osc_message import OscMessage

    def query_ableton(address, params=None, listen_port=11001):
        """Send an OSC query to port 11000 and return Ableton's reply from port 11001."""
        if params is None:
            params = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.5)
            sock.bind(("127.0.0.1", listen_port))
        
            client.send_message(address, params)
            data, _ = sock.recvfrom(65535)
            return OscMessage(data).params

    # Ask Ableton for the names of all tracks in your currently open Live Set
    track_names = query_ableton("/live/song/get/track_names")

    mo.md(f"**Tracks currently loaded in Ableton:** {', '.join(str(t) for t in track_names)}")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
