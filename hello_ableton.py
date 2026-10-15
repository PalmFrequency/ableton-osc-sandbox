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
def _():
    return


if __name__ == "__main__":
    app.run()
