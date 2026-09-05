"""
Cortex — FastAPI Backend & Real-Time Brain Server
Connects the UI to the Core Cortex Brain (Multimodal Vision, Web Research, Persistent Memory, Hardware Actuation).
"""

import asyncio
import json
import queue
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


async def serial_stream_broadcaster():
    """Continuously flush real-time incoming and outgoing serial lines to WebSocket clients."""
    while True:
        try:
            lines = []
            while not brain.device.worker.new_logs_queue.empty():
                try:
                    lines.append(brain.device.worker.new_logs_queue.get_nowait())
                except queue.Empty:
                    break
            if lines and clients:
                combined = "\n".join(lines)
                await broadcast({
                    "type": "arduino_serial_output",
                    "content": combined,
                    "replace": False
                })
        except Exception:
            pass
        await asyncio.sleep(0.1)


@app.on_event("startup")
async def on_startup():
    brain.camera.start_background_daemon()
    asyncio.create_task(serial_stream_broadcaster())

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

    elif msg_type == "arduino_set_pin":
        pin = message.get("pin")
        state = int(message.get("state", 0))
        # Actuate physical pin asynchronously
        success = await brain.device.set_pin_async(pin, state)
        
        # Track pin state in memory
        pin_key = str(pin).upper()
        if not pin_key.startswith("D") and not pin_key.startswith("A"):
            pin_key = f"D{pin_key}"
        brain.active_sketch.setdefault("pin_map", {})[pin_key] = state
        
        # Broadcast updated telemetry to all connected tabs
        await broadcast({
            "type": "arduino_telemetry",
            "data": brain.get_arduino_workbench_state()
        })
        
        state_str = "HIGH (ON)" if state else "LOW (OFF)"
        await broadcast({
            "type": "chat_message",
            "role": "system",
            "content": f"Hardware Switch: Pin {pin_key} set to {state_str}."
        })

    elif msg_type == "get_serial_output":
        output = brain.device.get_serial_output_sync(lines=50)
        await ws.send_json({
            "type": "arduino_serial_output",
            "content": output,
            "replace": True
        })

    elif msg_type == "clear_serial_log":
        await brain.device.clear_serial_output()
        await ws.send_json({
            "type": "arduino_serial_output",
            "content": "[INIT] Serial log cleared.",
            "replace": True
        })

    elif msg_type == "clear_memory":
        brain.conv_memory.clear_session("default")
        await broadcast({
            "type": "chat_message",
            "role": "system",
            "content": "Conversation memory and history cleared. Ready for fresh interaction."
        })

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
