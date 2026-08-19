# 🧠 Local Robot Brain — Neural Sensory Cortex

A fully local, multimodal **Vision-Language-Action** brain that:
- 👁️ Sees your live surroundings via **Camo Camera** (phone as webcam)
- 🧠 Reasons using **Qwen2.5-VL 7B** (locally via Ollama, GPU-accelerated)
- 🎙️ Listens with **Faster-Whisper STT** (Push-to-Talk or hands-free VAD)
- 🔊 Speaks back in a crisp **Neural Male Voice** (Edge-TTS)
- 🖥️ Runs in a **Cyberpunk HUD Cockpit** — fully in the browser

---

## Hardware Requirements
- NVIDIA GPU with ≥6GB VRAM (tested on RTX 3050 8GB)
- Camo Studio (phone as virtual webcam)
- Windows 10/11

---

## Quick Start

### 1. Install Ollama & pull the VL model
```cmd
winget install Ollama.Ollama
ollama pull qwen2.5vl:7b
```

### 2. Create Python environment & install dependencies
```cmd
uv venv --python 3.11
uv pip install -r backend/requirements.txt
```

### 3. Launch the Brain
Double-click `start_brain.bat` — or:
```cmd
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Project Structure
```
local-robot-brain/
├── backend/
│   ├── app.py              # FastAPI server + WebSocket streaming
│   ├── vision_brain.py     # Qwen2.5-VL vision reasoning engine
│   ├── camera_stream.py    # Camo Camera MSMF/DSHOW capture
│   ├── tts_engine.py       # Neural male voice (Edge-TTS)
│   ├── stt_engine.py       # Faster-Whisper speech-to-text
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Cyberpunk HUD Cockpit UI
│   ├── styles.css          # Glassmorphism neon dark theme
│   ├── app.js              # WebSocket + Push-to-Talk controller
│   └── audio_visualizer.js # Real-time audio spectrum canvas
├── start_brain.bat         # One-click launcher
└── test_pipeline.py        # Sanity test for all subsystems
```

---

## Usage
- **Hold Spacebar** (or the mic button) → speak your query → release to send
- Click **👁️ SCAN SCENE** for an autonomous environmental briefing
- Switch voices (*Guy, Christopher, Eric, Ryan*) or models live from the HUD
