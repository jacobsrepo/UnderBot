import os
import sys
import io
import time
import json
import base64
import asyncio
import signal
from typing import Optional, List, Dict

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

app = FastAPI(
    title="VLA Studio",
    description="Executive Multimodal Interface for Local Vision-Language-Action.",
    version="3.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache-busting middleware for static files
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response: Response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Core Instances
camera = CameraManager(device_index=0)
brain = VisionBrain()
tts = TTSEngine(default_voice_key="guy")
stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")

@app.on_event("startup")
async def startup_event():
    print("[Server] VLA Studio server online.")

@app.on_event("shutdown")
async def shutdown_event():
    print("[Server] Terminating tasks and releasing resources...")
    camera.stop()
    brain.shutdown()

@app.get("/favicon.ico")
def get_favicon():
    return Response(status_code=204)

# ==================== REST API ENDPOINTS ====================

@app.get("/api/status")
async def get_system_status():
    cam_stats = camera.get_stats()
    brain_stats = brain.get_status()
    return {
        "status": "online",
        "brain": brain_stats,
        "camera": cam_stats,
        "selected_voice": tts.default_voice_key,
        "active_voice_name": tts.AVAILABLE_VOICES.get(tts.default_voice_key, {}).get("name", "Guy")
    }

@app.get("/api/diagnostics")
async def get_diagnostics():
    return {
        "brain": brain.get_status(),
        "camera": camera.get_stats(),
        "voice": tts.default_voice_key
    }

@app.post("/api/system/shutdown")
async def shutdown_system(background_tasks: BackgroundTasks):
    print("[Server] Executing system shutdown...")
    
    def kill_process():
        time.sleep(0.5)
        camera.stop()
        brain.shutdown()
        os.kill(os.getpid(), signal.SIGTERM if sys.platform != "win32" else signal.SIGINT)

    background_tasks.add_task(kill_process)
    return {"success": True, "message": "Server and model engine terminated."}

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

class FrameUploadRequest(BaseModel):
    image_base64: str

@app.post("/api/camera/frame")
def upload_browser_frame(req: FrameUploadRequest):
    camera.update_client_frame(req.image_base64)
    return {"success": True}

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
    result = await tts.synthesize_base64(req.text, req.voice_key)
    return result

@app.post("/api/stt/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    fmt = file.filename.split(".")[-1] if file.filename and "." in file.filename else "wav"
    result = stt.transcribe_audio_bytes(audio_bytes, file_format=fmt)
    return result

class AnalyzeRequest(BaseModel):
    prompt: str
    image_base64: Optional[str] = None

@app.post("/api/brain/analyze")
async def analyze_scene(req: AnalyzeRequest):
    b64_frame = req.image_base64 or camera.get_latest_frame_base64() or ""
    analysis = await brain.analyze_frame_async(
        image_base64=b64_frame,
        user_prompt=req.prompt
    )
    if analysis.get("success") and analysis.get("response"):
        speech = await tts.synthesize_base64(analysis["response"])
        analysis["speech"] = speech
    return analysis

# ==================== WEBSOCKET LIVE STREAMING ====================

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()

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

            elif msg_type == "client_frame":
                b64 = msg.get("image_base64", "")
                if b64:
                    camera.update_client_frame(b64)

            elif msg_type == "text_query":
                user_text = msg.get("text", "")
                custom_frame = msg.get("image_base64")
                
                await websocket.send_json({
                    "type": "status_update",
                    "state": "thinking",
                    "query": user_text
                })

                frame_b64 = custom_frame or camera.get_latest_frame_base64() or ""

                res = await brain.analyze_frame_async(
                    image_base64=frame_b64,
                    user_prompt=user_text
                )
                
                reply_text = res.get("response", "")
                speech_data = await tts.synthesize_base64(reply_text)

                await websocket.send_json({
                    "type": "brain_response",
                    "query": user_text,
                    "response": reply_text,
                    "model": res.get("model", ""),
                    "latency_seconds": res.get("latency_seconds", 0),
                    "speech": speech_data
                })

            elif msg_type == "audio_query":
                audio_b64 = msg.get("audio_base64", "")
                audio_fmt = msg.get("format", "webm")
                custom_frame = msg.get("image_base64")

                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    await websocket.send_json({"type": "status_update", "state": "transcribing"})

                    stt_res = stt.transcribe_audio_bytes(audio_bytes, file_format=audio_fmt)
                    transcribed_text = stt_res.get("text", "")

                    if transcribed_text:
                        await websocket.send_json({"type": "stt_result", "text": transcribed_text})
                        await websocket.send_json({"type": "status_update", "state": "thinking", "query": transcribed_text})

                        frame_b64 = custom_frame or camera.get_latest_frame_base64() or ""

                        res = await brain.analyze_frame_async(
                            image_base64=frame_b64,
                            user_prompt=transcribed_text
                        )
                        reply_text = res.get("response", "")
                        speech_data = await tts.synthesize_base64(reply_text)

                        await websocket.send_json({
                            "type": "brain_response",
                            "query": transcribed_text,
                            "response": reply_text,
                            "model": res.get("model", ""),
                            "latency_seconds": res.get("latency_seconds", 0),
                            "speech": speech_data
                        })
                    else:
                        await websocket.send_json({"type": "status_update", "state": "idle", "message": "No speech detected."})

            elif msg_type == "scene_scan":
                custom_frame = msg.get("image_base64")
                frame_b64 = custom_frame or camera.get_latest_frame_base64() or ""
                prompt = "Give a concise 2-sentence description of the visual scene in front of the camera."

                res = await brain.analyze_frame_async(image_base64=frame_b64, user_prompt=prompt)
                reply_text = res.get("response", "")
                speech_data = await tts.synthesize_base64(reply_text)

                await websocket.send_json({
                    "type": "scene_briefing",
                    "response": reply_text,
                    "model": res.get("model", ""),
                    "speech": speech_data,
                    "latency_seconds": res.get("latency_seconds", 0)
                })

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
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
