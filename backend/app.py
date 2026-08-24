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
from brain import Brain
from vision_engine import VisionEngine
from tts_engine import TTSEngine
from stt_engine import STTEngine
from ssl_helper import get_local_ip, ensure_ssl_certificates, get_network_details
from desktop_agent import DesktopAgent
from embedded_agent import EmbeddedAgent
from intent_router import IntentRouter
from cognitive_core import CognitiveCore

app = FastAPI(
    title="Contender AI Assistant",
    description="Dual-Engine Tactical Assistant with Decoupled Qwen2.5-Coder Engine & On-Demand Vision.",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response: Response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Subsystems
camera = CameraManager(device_index=0)
primary_brain = Brain()
vision_engine = VisionEngine()
tts = TTSEngine(default_voice_key="guy")
stt = STTEngine(model_size="small.en", device="cpu", compute_type="int8")
desktop = DesktopAgent()
embedded = EmbeddedAgent()
router = IntentRouter()
core = CognitiveCore(desktop, embedded, primary_brain, vision_engine)

@app.on_event("startup")
async def startup_event():
    print("[Contender] Decoupled Coder-Brain & On-Demand Vision Core online.")

@app.on_event("shutdown")
async def shutdown_event():
    print("[Contender] Powering down subsystems...")
    camera.stop()
    embedded.disconnect_serial()
    primary_brain.shutdown()

@app.get("/favicon.ico")
def get_favicon():
    return Response(status_code=204)

# ==================== SYSTEM & STATUS REST APIS ====================

@app.get("/api/status")
async def get_system_status():
    return {
        "status": "online",
        "brain": primary_brain.get_status(),
        "active_engine": core.active_mode,
        "camera": camera.get_stats(),
        "network": get_network_details(8000, is_https=os.path.exists("certs/cert.pem")),
        "ports": embedded.detect_boards(),
        "metrics": desktop.get_system_metrics(),
        "selected_voice": tts.default_voice_key,
        "active_voice_name": tts.AVAILABLE_VOICES.get(tts.default_voice_key, {}).get("name", "Guy")
    }

@app.get("/api/diagnostics")
async def get_diagnostics():
    return {
        "brain": primary_brain.get_status(),
        "active_engine": core.active_mode,
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
    def kill_process():
        time.sleep(0.5)
        camera.stop()
        embedded.disconnect_serial()
        primary_brain.shutdown()
        os.kill(os.getpid(), signal.SIGTERM if sys.platform != "win32" else signal.SIGINT)

    background_tasks.add_task(kill_process)
    return {"success": True, "message": "Contender powered down."}

# ==================== DESKTOP AUTOMATION APIS ====================

@app.get("/api/desktop/metrics")
def get_metrics():
    return desktop.get_system_metrics()

class LaunchAppRequest(BaseModel):
    app_name: str

@app.post("/api/desktop/app/launch")
def launch_app(req: LaunchAppRequest):
    return desktop.launch_application(req.app_name)

@app.post("/api/desktop/windows/minimize")
def minimize_windows():
    return desktop.minimize_all_windows()

@app.post("/api/desktop/windows/restore")
def restore_windows():
    return desktop.undo_minimize_all()

@app.post("/api/desktop/organize")
def organize_desktop():
    return desktop.organize_desktop_files()

@app.get("/api/desktop/ocr")
def run_screen_ocr():
    return desktop.extract_screen_text()

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

# ==================== EMBEDDED HARDWARE APIS ====================

@app.get("/api/embedded/boards")
def get_boards():
    return embedded.detect_boards()

@app.get("/api/embedded/ports")
def get_serial_ports():
    return embedded.detect_boards()

class ProgramMicrocontrollerRequest(BaseModel):
    prompt: str
    board_hint: Optional[str] = "auto"

@app.post("/api/embedded/program")
async def auto_program_board(req: ProgramMicrocontrollerRequest):
    return await asyncio.to_thread(embedded.auto_compile_and_flash_sketch, req.prompt, req.board_hint or "auto")

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

# ==================== CAMERA & VOICE APIS ====================

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

# ==================== WEBSOCKET LIVE DISPATCH ====================

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

    async def send_progress_update(message: str):
        try:
            await websocket.send_json({
                "type": "progress_update",
                "message": message
            })
        except Exception:
            pass

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
                    "brain": primary_brain.get_status(),
                    "active_engine": core.active_mode
                })

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
                
                dispatch_res = await core.process_user_directive(
                    text=user_text,
                    intent_info=intent_res,
                    screen_b64=screen_b64,
                    cam_b64=cam_b64,
                    progress_cb=lambda m: asyncio.create_task(send_progress_update(m))
                )

                reply_text = dispatch_res["reply"]
                speech_data = await tts.synthesize_base64(reply_text)

                await websocket.send_json({
                    "type": "brain_response",
                    "query": user_text,
                    "response": reply_text,
                    "action_card": dispatch_res.get("action_card"),
                    "auto_vision": dispatch_res.get("active_vision", "screen"),
                    "active_engine": dispatch_res.get("active_engine", "CODER_ENGINE"),
                    "requires_confirmation": dispatch_res.get("requires_confirmation", False),
                    "model": "Qwen2.5-Coder Engine",
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

                    dispatch_res = await core.process_user_directive(
                        text=transcribed_text,
                        intent_info=intent_res,
                        screen_b64=screen_b64,
                        cam_b64=cam_b64,
                        progress_cb=lambda m: asyncio.create_task(send_progress_update(m))
                    )

                    reply_text = dispatch_res["reply"]
                    speech_data = await tts.synthesize_base64(reply_text)

                    await websocket.send_json({
                        "type": "brain_response",
                        "query": transcribed_text,
                        "response": reply_text,
                        "action_card": dispatch_res.get("action_card"),
                        "auto_vision": dispatch_res.get("active_vision", "screen"),
                        "active_engine": dispatch_res.get("active_engine", "CODER_ENGINE"),
                        "requires_confirmation": dispatch_res.get("requires_confirmation", False),
                        "model": "Qwen2.5-Coder Engine",
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
    except Exception:
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
