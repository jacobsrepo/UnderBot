import os
import sys
import io
import time
import json
import base64
import asyncio
from typing import Optional, List, Dict

# Ensure the backend directory is always on sys.path so sibling modules are importable
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
    title="Local Robot Brain Sensory Cortex",
    description="Multimodal Live Vision, Voice, and Cognitive Loop powered by Qwen-VL, Faster-Whisper, and Edge-TTS.",
    version="1.0.0"
)

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Component Instances
camera = CameraManager(device_index=0)
brain = VisionBrain(ollama_url="http://127.0.0.1:11434", default_model="qwen2.5vl:7b")
tts = TTSEngine(default_voice_key="guy")
stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")

# Startup lifecycle
@app.on_event("startup")
async def startup_event():
    print("[Server] Starting Local Robot Brain...")
    # Attempt to start camera index 0 (Camo Studio)
    try:
        camera.start(0)
    except Exception as e:
        print(f"[Server] Camera start warning: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    print("[Server] Shutting down camera...")
    camera.stop()

# ==================== REST API ENDPOINTS ====================

@app.get("/api/status")
async def get_system_status():
    ollama_info = brain.check_ollama_status()
    cam_stats = camera.get_stats()
    return {
        "status": "online",
        "camera": cam_stats,
        "ollama": ollama_info,
        "selected_model": brain.default_model,
        "selected_voice": tts.default_voice_key,
        "active_voice_name": tts.AVAILABLE_VOICES.get(tts.default_voice_key, {}).get("name", "Guy")
    }

@app.get("/api/camera/stream")
def video_feed():
    """Live MJPEG Video Feed for direct browser img tag embedding"""
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

@app.get("/api/camera/snapshot")
def get_snapshot():
    b64 = camera.get_latest_frame_base64()
    if not b64:
        return JSONResponse({"error": "No frame captured yet"}, status_code=503)
    return {"image_base64": b64, "timestamp": time.time()}

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
    model: Optional[str] = None

@app.post("/api/brain/analyze")
async def analyze_scene(req: AnalyzeRequest):
    b64_frame = camera.get_latest_frame_base64()
    analysis = await brain.analyze_frame_async(
        image_base64=b64_frame or "",
        user_prompt=req.prompt,
        model_name=req.model
    )
    # Automatically generate speech for the response
    if analysis.get("success") and analysis.get("response"):
        speech = await tts.synthesize_base64(analysis["response"])
        analysis["speech"] = speech
    return analysis

class ModelSelectRequest(BaseModel):
    model_name: str

@app.post("/api/brain/model")
def select_model(req: ModelSelectRequest):
    brain.set_model(req.model_name)
    return {"success": True, "model": brain.default_model}

# ==================== WEBSOCKET LIVE STREAMING ====================

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected to live sensory loop.")
    
    try:
        # Send initial handshake state
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

            elif msg_type == "text_query":
                user_text = msg.get("text", "")
                await websocket.send_json({
                    "type": "status_update",
                    "state": "thinking",
                    "query": user_text
                })

                # Capture latest live frame from Camo
                frame_b64 = camera.get_latest_frame_base64() or ""

                # Run VLM reasoning
                res = await brain.analyze_frame_async(
                    image_base64=frame_b64,
                    user_prompt=user_text
                )
                
                reply_text = res.get("response", "")

                # Synthesize male voice
                speech_data = await tts.synthesize_base64(reply_text)

                await websocket.send_json({
                    "type": "brain_response",
                    "query": user_text,
                    "response": reply_text,
                    "tokens_per_sec": res.get("tokens_per_sec", 0),
                    "latency_seconds": res.get("latency_seconds", 0),
                    "speech": speech_data
                })

            elif msg_type == "audio_query":
                # Audio blob uploaded via WebSocket
                audio_b64 = msg.get("audio_base64", "")
                audio_fmt = msg.get("format", "wav")
                
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    await websocket.send_json({
                        "type": "status_update",
                        "state": "transcribing"
                    })
                    
                    stt_res = stt.transcribe_audio_bytes(audio_bytes, file_format=audio_fmt)
                    transcribed_text = stt_res.get("text", "")

                    if transcribed_text:
                        await websocket.send_json({
                            "type": "stt_result",
                            "text": transcribed_text
                        })
                        
                        await websocket.send_json({
                            "type": "status_update",
                            "state": "thinking",
                            "query": transcribed_text
                        })

                        # Capture live snapshot
                        frame_b64 = camera.get_latest_frame_base64() or ""

                        # Reason through VisionBrain
                        res = await brain.analyze_frame_async(
                            image_base64=frame_b64,
                            user_prompt=transcribed_text
                        )
                        reply_text = res.get("response", "")

                        # Synthesize male voice
                        speech_data = await tts.synthesize_base64(reply_text)

                        await websocket.send_json({
                            "type": "brain_response",
                            "query": transcribed_text,
                            "response": reply_text,
                            "tokens_per_sec": res.get("tokens_per_sec", 0),
                            "latency_seconds": res.get("latency_seconds", 0),
                            "speech": speech_data
                        })
                    else:
                        await websocket.send_json({
                            "type": "status_update",
                            "state": "idle",
                            "message": "No audible speech detected."
                        })

            elif msg_type == "scene_scan":
                # Autonomous Environmental Observation
                frame_b64 = camera.get_latest_frame_base64() or ""
                prompt = "Scan this scene. Give a brief, high-level situational awareness briefing of what is in front of the camera in 2 short sentences."
                
                res = await brain.analyze_frame_async(
                    image_base64=frame_b64,
                    user_prompt=prompt
                )
                reply_text = res.get("response", "")
                speech_data = await tts.synthesize_base64(reply_text)

                await websocket.send_json({
                    "type": "scene_briefing",
                    "response": reply_text,
                    "speech": speech_data,
                    "latency_seconds": res.get("latency_seconds", 0)
                })

            elif msg_type == "set_voice":
                voice_k = msg.get("voice_key", "guy")
                tts.set_voice(voice_k)
                await websocket.send_json({
                    "type": "voice_updated",
                    "voice_key": tts.default_voice_key
                })

            elif msg_type == "set_model":
                model_n = msg.get("model_name", "qwen2.5-vl:7b")
                brain.set_model(model_n)
                await websocket.send_json({
                    "type": "model_updated",
                    "model_name": brain.default_model
                })

    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")
    except Exception as e:
        print(f"[WebSocket] Error in loop: {e}")

# Mount static files for Frontend Cockpit UI
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
