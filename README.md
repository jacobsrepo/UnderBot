# VLA Studio - Local Multimodal Vision & Voice Architecture

A fully self-contained, local Vision-Language-Action (VLA) interface designed for real-time visual reasoning, speech transcription, and natural conversational response.

---

## Overview

VLA Studio provides an end-to-end multimodal perception loop running entirely on local hardware:
- **Visual Reasoning**: Embedded Qwen2.5-VL 7B executing directly on local GPU via a standalone CUDA engine.
- **Speech Recognition**: Low-latency speech-to-text powered by Faster-Whisper.
- **Speech Synthesis**: Neural male voice output for direct conversational dialogue.
- **Multi-Camera Capture**: Direct support for browser-based webcams (via WebRTC) and host-connected cameras (Camo Studio, USB webcams, integrated sensors).
- **Diagnostics & Control**: Real-time engine readiness indicators and one-click system power-off controls.

---

## System Architecture

```
local-robot-brain/
|-- bin/llama/              # Standalone CUDA model execution engine
|   |-- llama-server.exe
|   `-- cudart64_12.dll
|-- models/
|   `-- qwen2.5vl-7b.gguf   # Local Qwen2.5-VL model weights (5.56 GB)
|-- backend/
|   |-- app.py              # FastAPI server and lifecycle manager
|   |-- vision_brain.py     # In-process neural model controller and diagnostics
|   |-- camera_stream.py    # DirectShow and WebRTC camera stream coordinator
|   |-- tts_engine.py       # Neural speech synthesis engine
|   |-- stt_engine.py       # Faster-Whisper speech transcription engine
|   `-- requirements.txt
|-- frontend/               # Professional workspace UI
|   |-- index.html
|   |-- styles.css
|   |-- app.js
|   `-- audio_visualizer.js
`-- start_brain.bat         # Standalone system launcher
```

---

## Installation & Setup

### 1. Requirements
- Windows 10/11, Linux, or macOS
- Python 3.10+
- Dedicated GPU with CUDA support recommended for acceleration

### 2. Environment Setup
```cmd
uv venv --python 3.11
uv pip install -r backend/requirements.txt
```

### 3. Launching the System
Execute the launcher script:
```cmd
start_brain.bat
```
Or start the server manually:
```cmd
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Navigate to `http://localhost:8000` in any web browser.

---

## Usage Instructions

- **Hold Spacebar** or click the push-to-talk button to record a question about the visual feed.
- Click **Scan Scene** to trigger an autonomous environmental summary.
- Click **Analyze Frame** in the visual viewport to query the current camera snapshot.
- Click **Stop System** in the header navigation to cleanly terminate all model processes and shut down the server.
