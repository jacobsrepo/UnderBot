# Contender - Tactical Desktop AI Assistant & Hardware Engineer

A fully self-contained, local multimodal assistant featuring continuous screen perception, on-demand camera vision, Windows desktop OS automation, on-the-fly Arduino & ESP microcontroller programming, and a native desktop shell with an Always-on-Top Floating Mini HUD.

---

## 1. Core Architecture & Persona

- **Persona**: **Contender** — a tactical, razor-sharp male AI partner inspired by the personality of Cortana from Halo. Calm under pressure, highly competent, witty, concise, and mission-focused.
- **Continuous Screen Perception**: Continuously perceives your desktop screen by default for code debugging, reading documentation, and inspecting UI workflows.
- **On-Demand Camera Vision**: Physical camera feed is summoned on-demand when inspecting physical objects or real-world surroundings.
- **Native Desktop Shell & Mini HUD**: Runs as a standalone Windows application with Microsoft Edge WebView2. Minimizing or toggling switches Contender into a sleek, draggable, Always-on-Top floating companion pill.
- **Hardware & Microcontroller Engineering**: On-the-fly Arduino and ESP32/ESP8266 COM port auto-discovery, code generation, firmware flashing via `esptool`, and a live interactive two-way serial monitor.
- **Desktop OS Automation**: File management (copy, move, delete, organize, search), application launching (VS Code, Chrome, Terminal, etc.), system metrics, and safe PowerShell execution.
- **Directed Speech & Wake Word**: Recognizes when you address him (*"Contender"*, *"Hey Contender"*, *"Computer"*) and maintains conversation threads without repeating the wake word.

---

## 2. Directory Structure

```
UnderBot/
|-- backend/
|   |-- app.py              # FastAPI server & WebSocket action coordinator
|   |-- brain.py            # Primary Coder Brain (Async aiohttp, Qwen2.5-Coder / OpenAI API)
|   |-- cognitive_core.py   # Dual-Engine Router, Safety Interceptor & C++ Reflector
|   |-- vision_engine.py    # Secondary Perception Engine (RapidOCR & Visual Snapshots)
|   |-- desktop_agent.py    # Desktop OS automation, Recycle Bin ops & window focus
|   |-- embedded_agent.py   # Arduino/ESP port detection, flashing & serial monitor
|   |-- intent_router.py    # Directed speech & wake-word analyzer
|   |-- camera_stream.py    # DirectShow / WebRTC video pipeline
|   |-- ssl_helper.py       # Local LAN TLS certificate manager
|   |-- tts_engine.py       # Male neural speech synthesizer
|   |-- stt_engine.py       # Faster-Whisper GPU/CPU speech-to-text
|   `-- requirements.txt
|-- frontend/               # Contender Tactical Studio & Mini HUD
|   |-- index.html
|   |-- styles.css
|   |-- app.js
|   `-- audio_visualizer.js
|-- desktop_shell.py        # Native Windows WebView2 shell & Mini HUD manager
|-- test_desktop_agent.py   # Subsystem verification suite
|-- test_pipeline.py        # Full multimodal pipeline test suite
`-- start_brain.bat         # One-click launcher
```

---

## 3. Quick Start

### Installation
```cmd
uv venv --python 3.11
uv pip install -r backend/requirements.txt
```

### Launching
Double-click:
```cmd
start_brain.bat
```
* Launches the **Contender Native Tactical Studio**.
* Click **Mini HUD** in the top navigation bar to collapse Contender into a sleek floating Always-on-Top companion widget while you work.

---

## 4. Voice Commands Examples

- *"Contender, what error is on my screen?"*
- *"Contender, launch VS Code and organize my Desktop files."*
- *"Contender, scan COM ports and write an ESP32 Wi-Fi telemetry sketch."*
- *"Contender, check my CPU and RAM usage."*
- *"Contender, switch to camera and tell me what I'm holding."*
