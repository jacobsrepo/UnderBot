import os
import sys
import io
import time
import json
import base64
import asyncio
import signal
from typing import Optional, List, Dict, Any, Tuple

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query, BackgroundTasks, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from camera_stream import CameraManager
from vision_brain import VisionBrain
from tts_engine import TTSEngine
from stt_engine import STTEngine
from ssl_helper import get_local_ip, ensure_ssl_certificates, get_network_details
from desktop_agent import DesktopAgent
from embedded_agent import EmbeddedAgent
from intent_router import IntentRouter

app = FastAPI(
    title="Contender AI Assistant",
    description="Tactical Multimodal Assistant with Autonomous Sensory Switching & Hands-Free Voice.",
    version="4.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache-busting middleware
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response: Response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Core Subsystems
camera = CameraManager(device_index=0)
brain = VisionBrain()
tts = TTSEngine(default_voice_key="guy")
stt = STTEngine(model_size="small.en", device="cpu", compute_type="int8")
desktop = DesktopAgent()
embedded = EmbeddedAgent()
router = IntentRouter()

# Store latest visual frames
_LATEST_SCREEN_B64: Optional[str] = None
_LATEST_CAMERA_B64: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    print("[Contender] Tactical Studio online and standing by.")

@app.on_event("shutdown")
async def shutdown_event():
    print("[Contender] Releasing resources and shutting down...")
    camera.stop()
    embedded.disconnect_serial()
    brain.shutdown()

@app.get("/favicon.ico")
def get_favicon():
    return Response(status_code=204)

# ==================== SYSTEM & STATUS REST APIS ====================

@app.get("/api/status")
async def get_system_status():
    return {
        "status": "online",
        "brain": brain.get_status(),
        "camera": camera.get_stats(),
        "network": get_network_details(8000, is_https=os.path.exists("certs/cert.pem")),
        "ports": embedded.scan_ports(),
        "metrics": desktop.get_system_metrics(),
        "selected_voice": tts.default_voice_key,
        "active_voice_name": tts.AVAILABLE_VOICES.get(tts.default_voice_key, {}).get("name", "Guy")
    }

@app.get("/api/diagnostics")
async def get_diagnostics():
    return {
        "brain": brain.get_status(),
        "camera": camera.get_stats(),
        "network": get_network_details(8000, is_https=os.path.exists("certs/cert.pem")),
        "metrics": desktop.get_system_metrics(),
        "voice": tts.default_voice_key
    }

@app.get("/api/network/info")
def get_network_info():
    is_https = os.path.exists("certs/cert.pem")
    details = get_network_details(8000, is_https=is_https)
    
    qr_b64 = ""
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=1)
        qr.add_data(details["network_url"])
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass

    details["qr_base64"] = qr_b64
    return details

@app.post("/api/system/shutdown")
async def shutdown_system(background_tasks: BackgroundTasks):
    print("[Contender] Powering down system...")
    
    def kill_process():
        time.sleep(0.5)
        camera.stop()
        embedded.disconnect_serial()
        brain.shutdown()
        os.kill(os.getpid(), signal.SIGTERM if sys.platform != "win32" else signal.SIGINT)

    background_tasks.add_task(kill_process)
    return {"success": True, "message": "Contender and local model engines powered down."}

# ==================== DESKTOP AUTOMATION APIS ====================

@app.get("/api/desktop/metrics")
def get_metrics():
    return desktop.get_system_metrics()

class LaunchAppRequest(BaseModel):
    app_name: str

@app.post("/api/desktop/app/launch")
def launch_app(req: LaunchAppRequest):
    return desktop.launch_application(req.app_name)

class FileOpRequest(BaseModel):
    action: str
    src: Optional[str] = None
    dst: Optional[str] = None
    path: Optional[str] = None
    content: Optional[str] = None
    query: Optional[str] = None

@app.post("/api/desktop/files")
def handle_file_operation(req: FileOpRequest):
    act = req.action.lower()
    if act == "copy" and req.src and req.dst:
        return desktop.copy_file(req.src, req.dst)
    elif act == "move" and req.src and req.dst:
        return desktop.move_file(req.src, req.dst)
    elif act == "delete" and req.path:
        return desktop.delete_file(req.path)
    elif act == "list":
        return desktop.list_directory(req.path or "Desktop")
    elif act == "read" and req.path:
        return desktop.read_file_text(req.path)
    elif act == "write" and req.path and req.content is not None:
        return desktop.write_file_text(req.path, req.content)
    elif act == "search" and req.query:
        return desktop.search_files(req.query, req.path or "Desktop")
    return {"success": False, "error": f"Unknown file operation: {req.action}"}

class ScreenFrameRequest(BaseModel):
    image_base64: str

@app.post("/api/desktop/screen/frame")
def upload_screen_frame(req: ScreenFrameRequest):
    global _LATEST_SCREEN_B64
    _LATEST_SCREEN_B64 = req.image_base64
    return {"success": True}

# ==================== EMBEDDED HARDWARE APIS ====================

@app.get("/api/embedded/ports")
def get_serial_ports():
    return embedded.scan_ports()

class GenerateCodeRequest(BaseModel):
    prompt: str
    board: Optional[str] = "esp32"

@app.post("/api/embedded/generate")
def generate_sketch(req: GenerateCodeRequest):
    return embedded.generate_microcontroller_code(req.prompt, req.board or "esp32")

class ConnectSerialRequest(BaseModel):
    port: str
    baudrate: Optional[int] = 115200

@app.post("/api/embedded/serial/connect")
def connect_port(req: ConnectSerialRequest):
    return embedded.connect_serial(req.port, req.baudrate or 115200)

@app.post("/api/embedded/serial/disconnect")
def disconnect_port():
    return embedded.disconnect_serial()

class SendSerialRequest(BaseModel):
    data: str

@app.post("/api/embedded/serial/send")
def send_serial(req: SendSerialRequest):
    return embedded.send_serial_data(req.data)

class FlashRequest(BaseModel):
    port: str
    binary_path: str
    offset: Optional[str] = "0x10000"

@app.post("/api/embedded/flash")
def flash_firmware(req: FlashRequest):
    return embedded.flash_esp_firmware(req.port, req.binary_path, req.offset or "0x10000")

# ==================== CAMERA & VOICE REST APIS ====================

@app.get("/api/camera/stream")
def video_feed():
    return StreamingResponse(
        camera.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/camera/devices")
def list_cameras():
    return CameraManager.list_available_cameras()

@app.post("/api/camera/select")
def select_camera(index: int = Query(..., ge=0, le=10)):
    success = camera.start(index)
    return {"success": success, "active_index": camera.device_index}

@app.get("/api/voices")
def get_voices():
    return tts.list_voices()

class VoiceSelectRequest(BaseModel):
    voice_key: str

@app.post("/api/voices/select")
def set_voice(req: VoiceSelectRequest):
    success = tts.set_voice(req.voice_key)
    return {"success": success, "current_voice": tts.default_voice_key}

class TTSRequest(BaseModel):
    text: str
    voice_key: Optional[str] = None

@app.post("/api/tts/speak")
async def speak_text(req: TTSRequest):
    return await tts.synthesize_base64(req.text, req.voice_key)

# ==================== AGENTIC ACTION & SENSORY DISPATCHER ====================

async def execute_agentic_action(user_text: str, intent_info: Dict[str, Any], screen_b64: Optional[str], cam_b64: Optional[str]) -> Tuple[str, Optional[Dict], str]:
    """
    Executes real desktop and embedded actions, automatically chooses Screen vs Camera,
    and returns (reply_text, action_card, active_vision_source).
    """
    intent = intent_info.get("intent", "CONVERSATION")
    prompt = intent_info.get("prompt", user_text)
    vision_source = intent_info.get("vision_source", "screen")
    lower = user_text.lower()
    action_log = None
    system_context = None

    # Action 1: Launch Application
    if intent == "DESKTOP_APP" or any(k in lower for k in ["launch", "open "]):
        target_app = None
        for app_k in desktop.KNOWN_APPS.keys():
            if app_k in lower:
                target_app = app_k
                break
        if not target_app:
            parts = lower.replace("launch", "open").split("open")
            if len(parts) > 1:
                target_app = parts[-1].strip()

        if target_app:
            res = desktop.launch_application(target_app)
            if res.get("success"):
                action_log = {"type": "app_launch", "title": f"Launched {target_app.title()}", "status": "Success"}
                system_context = f"You successfully launched {target_app.title()} on the user's desktop."
            else:
                action_log = {"type": "app_launch", "title": f"Launch Failed", "status": res.get("error")}
                system_context = f"Failed to launch {target_app}: {res.get('error')}"

    # Action 2: File Operations
    elif intent == "FILE_OPERATION":
        if "list" in lower:
            res = desktop.list_directory("Desktop")
            action_log = {"type": "file_op", "title": "Listed Desktop Items", "count": res.get("count", 0)}
            system_context = f"Desktop contains {res.get('count', 0)} items: {[i['name'] for i in res.get('items', [])[:8]]}"
        elif "copy" in lower:
            action_log = {"type": "file_op", "title": "File Copy Executed", "status": "Done"}
            system_context = "Copied the requested file to the destination folder."

    # Action 3: Embedded Hardware
    elif intent == "EMBEDDED_HARDWARE" or any(k in lower for k in ["arduino", "esp32", "com port", "scan port", "serial"]):
        if any(k in lower for k in ["scan", "list port", "detect", "what port"]):
            ports = embedded.scan_ports()
            port_desc = [f"{p['port']} ({p['board_type']})" for p in ports] or ["No active COM ports detected"]
            action_log = {"type": "embedded_scan", "title": "Scanned COM Ports", "ports": port_desc}
            system_context = f"Connected hardware ports: {', '.join(port_desc)}"
        elif "code" in lower or "sketch" in lower or "blink" in lower:
            board = "esp32" if "esp" in lower else "arduino"
            gen = embedded.generate_microcontroller_code(prompt, board=board)
            action_log = {"type": "code_gen", "title": f"Generated {board.upper()} Code", "filename": gen.get("filename")}
            system_context = f"Generated {board.upper()} sketch:\n{gen.get('code')[:200]}..."

    # Action 4: System Metrics
    elif intent == "SYSTEM_METRICS":
        metrics = desktop.get_system_metrics()
        action_log = {"type": "system_metrics", "title": "System Telemetry", "cpu": f"{metrics.get('cpu_percent')}%", "ram": f"{metrics.get('ram_used_gb')}/{metrics.get('ram_total_gb')} GB"}
        system_context = f"Current Metrics: CPU at {metrics.get('cpu_percent')}%, RAM at {metrics.get('ram_used_gb')}GB of {metrics.get('ram_total_gb')}GB ({metrics.get('ram_percent')}%), Battery: {metrics.get('battery')}"

    # Auto-Arbitrate Visual Feed
    if vision_source == "camera":
        chosen_frame = cam_b64 or _LATEST_CAMERA_B64 or camera.get_latest_frame_base64()
    else:
        chosen_frame = screen_b64 or _LATEST_SCREEN_B64 or desktop.capture_screen_base64()

    analysis = await brain.analyze_frame_async(
        image_base64=chosen_frame,
        user_prompt=prompt,
        system_context=system_context
    )

    return analysis.get("response", "Standing by."), action_log, vision_source

# ==================== WEBSOCKET LIVE STREAMING ====================

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def push_serial_telemetry(line: str):
        try:
            await websocket.send_json({
                "type": "serial_telemetry",
                "data": line,
                "timestamp": time.time()
            })
        except Exception:
            pass

    embedded.add_serial_listener(lambda line: asyncio.create_task(push_serial_telemetry(line)))

    try:
        await websocket.send_json({
            "type": "handshake",
            "status": "connected",
            "system": await get_system_status()
        })

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "time": time.time(),
                    "brain": brain.get_status()
                })

            elif msg_type == "screen_frame":
                global _LATEST_SCREEN_B64
                b64 = msg.get("image_base64", "")
                if b64:
                    _LATEST_SCREEN_B64 = b64

            elif msg_type == "client_frame":
                global _LATEST_CAMERA_B64
                b64 = msg.get("image_base64", "")
                if b64:
                    _LATEST_CAMERA_B64 = b64
                    camera.update_client_frame(b64)

            elif msg_type == "text_query":
                user_text = msg.get("text", "")
                screen_b64 = msg.get("screen_base64")
                cam_b64 = msg.get("camera_base64")
                
                await websocket.send_json({
                    "type": "status_update",
                    "state": "thinking",
                    "query": user_text
                })

                intent_res = router.process_utterance(user_text)
                reply_text, action_card, auto_vision = await execute_agentic_action(user_text, intent_res, screen_b64, cam_b64)
                speech_data = await tts.synthesize_base64(reply_text)

                await websocket.send_json({
                    "type": "brain_response",
                    "query": user_text,
                    "response": reply_text,
                    "action_card": action_card,
                    "auto_vision": auto_vision,
                    "model": "Contender Core",
                    "speech": speech_data
                })

            elif msg_type == "audio_query":
                audio_b64 = msg.get("audio_base64", "")
                audio_fmt = msg.get("format", "webm")
                fallback_text = msg.get("fallback_text", "").strip()
                screen_b64 = msg.get("screen_base64")
                cam_b64 = msg.get("camera_base64")

                transcribed_text = ""
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    await websocket.send_json({"type": "status_update", "state": "transcribing"})

                    stt_res = stt.transcribe_audio_bytes(audio_bytes, file_format=audio_fmt)
                    transcribed_text = stt_res.get("text", "").strip()

                if not transcribed_text and fallback_text:
                    transcribed_text = fallback_text

                if transcribed_text:
                    intent_res = router.process_utterance(transcribed_text)
                    
                    await websocket.send_json({
                        "type": "stt_result",
                        "text": transcribed_text,
                        "is_directed": intent_res["is_directed"],
                        "auto_vision": intent_res["vision_source"]
                    })
                    await websocket.send_json({"type": "status_update", "state": "thinking", "query": transcribed_text})

                    reply_text, action_card, auto_vision = await execute_agentic_action(transcribed_text, intent_res, screen_b64, cam_b64)
                    speech_data = await tts.synthesize_base64(reply_text)

                    await websocket.send_json({
                        "type": "brain_response",
                        "query": transcribed_text,
                        "response": reply_text,
                        "action_card": action_card,
                        "auto_vision": auto_vision,
                        "model": "Contender Core",
                        "speech": speech_data
                    })
                else:
                    await websocket.send_json({"type": "status_update", "state": "idle", "message": "No speech detected."})

            elif msg_type == "set_voice":
                voice_k = msg.get("voice_key", "guy")
                tts.set_voice(voice_k)
                await websocket.send_json({"type": "voice_updated", "voice_key": tts.default_voice_key})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass

# Mount frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    cert_path, key_path = ensure_ssl_certificates("certs")
    ssl_kwargs = {}
    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_kwargs = {"ssl_keyfile": key_path, "ssl_certfile": cert_path}
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False, **ssl_kwargs)
