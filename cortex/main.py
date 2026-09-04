"""
Cortex — FastAPI Backend & Real-Time Brain Server
Connects the UI to the Core Cortex Brain (Multimodal Vision, Web Research, Persistent Memory, Hardware Actuation).
"""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.brain import CortexBrain

app = FastAPI(title="Cortex Core")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Instantiate Core Brain ───────────────────────────────────────────
brain = CortexBrain()


@app.on_event("startup")
async def on_startup():
    brain.camera.start_background_daemon()

# ── Connected clients ────────────────────────────────────────────────
clients: set[WebSocket] = set()


async def broadcast(message: dict):
    """Send a message to every connected WebSocket client."""
    for client in clients.copy():
        try:
            await client.send_json(message)
        except Exception:
            clients.discard(client)


# ── Routes ───────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        # Send initial state and connected device registry
        await ws.send_json({"type": "state_change", "state": "idle"})
        await ws.send_json({
            "type": "device_update",
            "devices": [
                brain.get_hardware_status(),
                {
                    "name": "Vision Sensor",
                    "status": "online",
                    "detail": "WebRTC HD Webcam Stream",
                },
                {
                    "name": "Neural Voice (TTS)",
                    "status": "online",
                    "detail": "Edge-TTS Christopher (Male)",
                },
                {
                    "name": "Memory Core",
                    "status": "online",
                    "detail": "SQLite Persistent DB",
                }
            ],
        })

        while True:
            data = await ws.receive_text()
            message = json.loads(data)
            await handle_message(ws, message)

    except WebSocketDisconnect:
        clients.discard(ws)


# ── Message handlers ─────────────────────────────────────────────────
async def handle_message(ws: WebSocket, message: dict):
    msg_type = message.get("type")

    if msg_type == "chat_message":
        content = message.get("content", "")

        # Echo user prompt
        await broadcast({
            "type": "chat_message",
            "role": "user",
            "content": content,
        })

        # Process through Cortex Brain with error recovery
        try:
            await brain.process_user_message(content, broadcast)
        except Exception as e:
            print(f"[Backend Error] process_user_message failed: {e}")
            await broadcast({
                "type": "chat_message",
                "role": "system",
                "content": f"Processing error: {e}",
            })
            await broadcast({"type": "state_change", "state": "idle"})

    elif msg_type == "camera_frame":
        # Store latest frame snapshot for multimodal AI vision analysis
        frame = message.get("frame", "")
        if frame:
            brain.receive_camera_frame(frame)

    elif msg_type == "get_arduino_state":
        await ws.send_json({
            "type": "arduino_telemetry",
            "data": brain.get_arduino_workbench_state()
        })

    elif msg_type == "arduino_quick_action":
        action = message.get("action")
        if action == "test_pins":
            await brain.process_user_message("test all digital and analog pins on the arduino", broadcast)
        elif action == "clear_pins":
            await brain.process_user_message("turn off all pins on the arduino", broadcast)
        elif action == "check_hardware":
            await brain.process_user_message("check hardware connection", broadcast)

    elif msg_type == "demo_cycle":
        states = [
            ("listening", "Listening to microphone audio stream…"),
            ("thinking", "Analyzing neural knowledge graph and web documentation…"),
            ("seeing", "Inspecting circuit board through camera vision sensor…"),
            ("programming", "Actuating digital pin D3 on Arduino Nano…"),
            ("speaking", "Synthesizing voice response…"),
            ("idle", "Cycle complete. Standing by."),
        ]
        for state, description in states:
            await broadcast({"type": "state_change", "state": state})
            await broadcast({
                "type": "chat_message",
                "role": "system",
                "content": f"[{state.upper()}] {description}",
            })
            await asyncio.sleep(2.5)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
