import os
import sys
import io
import time
import json
import base64
import asyncio
from typing import Optional, List, Dict

# Ensure backend directory is in sys.path
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from camera_stream import CameraManager
from vision_brain import VisionBrain
from tts_engine import TTSEngine
from stt_engine import STTEngine

# Initialize FastAPI App
app = FastAPI(
    title="Universal Multimodal Vision-Voice Assistant",
    description="Flexible Vision-Language-Voice cockpit supporting local GPUs, cloud APIs, and browser webcams.",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Instances
camera = CameraManager(device_index=0)
brain = VisionBrain(ollama_url="http://127.0.0.1:11434", default_model="qwen2.5vl:7b")
tts = TTSEngine(default_voice_key="guy")
stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")

@app.on_event("startup")
async def startup_event():
    print("[Server] Starting Multimodal Assistant Server...")
    try:
        camera.start(0)
    except Exception as e:
        print(f"[Server] Note: Initial camera start: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    camera.stop()

# ==================== REST API ENDPOINTS ====================

@app.get("/api/status")
async def get_system_status():
    ollama_info = brain.check_ollama_status()
    cam_stats = camera.get_stats()
    return {
        "status": "online",
        "provider": brain.provider,
        "camera": cam_stats,
        "ollama": ollama_info,
        "selected_model": brain.default_model,
        "has_api_key": bool(brain.api_key),
        "selected_voice": tts.default_voice_key,
        "active_voice_name": tts.AVAILABLE_VOICES.get(tts.default_voice_key, {}).get("name", "Guy")
    }

class ConfigUpdateRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    voice: Optional[str] = None

@app.post("/api/config")
def update_config(req: ConfigUpdateRequest):
    brain.update_config(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
        api_base=req.api_base
    )
    if req.voice:
        tts.set_voice(req.voice)
    return {"success": True, "provider": brain.provider, "model": brain.default_model, "voice": tts.default_voice_key}

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
    model: Optional[str] = None

@app.post("/api/brain/analyze")
async def analyze_scene(req: AnalyzeRequest):
    b64_frame = req.image_base64 or camera.get_latest_frame_base64() or ""
    analysis = await brain.analyze_frame_async(
        image_base64=b64_frame,
        user_prompt=req.prompt,
        model_name=req.model
    )
    if analysis.get("success") and analysis.get("response"):
        speech = await tts.synthesize_base64(analysis["response"])
        analysis["speech"] = speech
    return analysis

# ==================== WEBSOCKET LIVE STREAMING ====================

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected.")

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
                await websocket.send_json({"type": "pong", "time": time.time()})

            elif msg_type == "client_frame":
                # Frame streamed from browser webcam
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
                    "tokens_per_sec": res.get("tokens_per_sec", 0),
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
                            "tokens_per_sec": res.get("tokens_per_sec", 0),
                            "latency_seconds": res.get("latency_seconds", 0),
                            "speech": speech_data
                        })
                    else:
                        await websocket.send_json({"type": "status_update", "state": "idle", "message": "No audible speech detected."})

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

            elif msg_type == "update_config":
                brain.update_config(
                    provider=msg.get("provider"),
                    model=msg.get("model"),
                    api_key=msg.get("api_key"),
                    api_base=msg.get("api_base")
                )
                if msg.get("voice"):
                    tts.set_voice(msg.get("voice"))
                await websocket.send_json({"type": "config_updated", "provider": brain.provider, "model": brain.default_model})

    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")

# Mount static frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
