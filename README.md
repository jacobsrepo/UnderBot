# VLA Studio - Local Multimodal Vision & Voice Architecture

A fully self-contained, local Vision-Language-Action (VLA) interface designed for real-time visual reasoning, speech transcription, and natural conversational dialogue across desktop and network-connected devices.

---

## Overview

VLA Studio provides an end-to-end multimodal perception loop running entirely on local hardware:
- **Visual Reasoning**: In-process Qwen2.5-VL executing directly on local GPU with 4-bit CUDA quantization.
- **Full HD 1080p Perception**: 1920x1080 high-framerate visual capture with frame inspection.
- **Universal Multi-Device Operation**: Connect any mobile phone, iPad, or laptop on the local Wi-Fi network to use its camera and microphone as sensory inputs.
- **Speech Recognition**: Low-latency speech-to-text powered by Faster-Whisper.
- **Speech Synthesis**: Neural male voice output for conversational responses.
- **Diagnostics & Control**: Real-time engine readiness indicators and one-click system power-off controls.

---

## System Architecture

```
local-robot-brain/
|-- backend/
|   |-- app.py              # FastAPI server and lifecycle manager
|   |-- vision_brain.py     # In-process PyTorch CUDA Qwen2.5-VL controller
|   |-- camera_stream.py    # 1080p WebRTC and DirectShow camera coordinator
|   |-- ssl_helper.py       # Local network TLS certificate manager
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
- Dedicated GPU with CUDA support recommended

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
python backend/app.py
```

---

## Multi-Device / Network Access

To use a smartphone, tablet, or another laptop as the camera and microphone:
1. Ensure both devices are connected to the same Wi-Fi network.
2. In the desktop interface, click **Connect Device** in the top navigation bar.
3. Scan the displayed **QR Code** with your phone's camera, or navigate directly to the printed network address (e.g. `https://<YOUR_LOCAL_IP>:8000`).
4. If a self-signed security prompt appears in your browser, select **Advanced -> Proceed** to grant camera and microphone permissions.
5. Tap **Flip** to toggle between front and rear cameras on mobile devices.
