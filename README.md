# UnderBot (Cortex Core) — Autonomous Multimodal AI Brain with Physical Agency & Live Vision

[![Branch](https://img.shields.io/badge/Branch-Local--VLA--Setup-blue.svg)](https://github.com/jacobsrepo/UnderBot/tree/Local-VLA-Setup)
[![Hardware](https://img.shields.io/badge/Hardware-Arduino%20Nano%20(COM4)-success.svg)](https://docs.arduino.cc/hardware/nano)
[![Model](https://img.shields.io/badge/LLM-Qwen2.5%207B%20Instruct-orange.svg)](https://ollama.com)
[![Vision](https://img.shields.io/badge/Vision-Moondream%20%2B%20OpenCV-purple.svg)](https://ollama.com)
[![Voice](https://img.shields.io/badge/Voice-Edge--TTS%20Male%20(Christopher)-cyan.svg)](https://github.com/rany2/edge-tts)

**UnderBot / Cortex** is a fully local, autonomous Vision-Language-Action (VLA) AI assistant featuring real-time multimodal vision, closed-loop physical hardware control, live web intelligence, persistent long-term memory, and full-duplex neural voice interaction.

---

## Key Capabilities

### 1. Autonomous ReAct Agent Loop
- **Zero Scripted Matching**: Every interaction is dynamically reasoned by local LLMs (`qwen2.5:7b-instruct-q4_K_M` via Ollama) executing multi-step tool calls.
- **Dynamic Tool Dispatch**: Autonomously calls hardware actuation, web surfing, visual inspection, weather polling, and memory recall tools.

### 2. Closed-Loop Hardware & Optical Vision (`vision/probe.py`)
- **Direct Microcontroller Actuation**: Connected to physical **Arduino Nano on `COM4` (115200 baud)** controlling 16 digital and analog IO pins (`D2` through `D13` and `A0` through `A5`).
- **Ground-Truth Optical Verification**: Real-time OpenCV optical emission analysis measures actual light wavelengths (Red, Green, Blue) to eliminate vision hallucinations.
- **Autonomous Pin Discovery**: Sequentially probes hardware pins while actively inspecting the live camera feed to discover which pin is wired to which component or LED on custom shields (such as the 16-LED Binary Clock shield).

### 3. Live Web Research Engine (`research/surfer.py`)
- **Real-Time Data Extraction**: Direct POST search scraping + full-page DOM parsing with `BeautifulSoup`.
- **Knowledge Grounding**: Fetches live web excerpts, documentation, and news, strictly grounding the agent's answers to eliminate outdated training data.

### 4. Neural Male Voice Pipeline (`tts/speaker.py` & `static/js/voice.js`)
- **Authoritative Male Voice**: Edge-TTS neural model **`en-US-ChristopherNeural`** generates natural, deep spoken responses.
- **Full-Duplex Speech Recognition (STT)**: Continuous browser speech recognition with wake-word and push-to-talk modes.
- **3-Layer Acoustic Echo Cancellation**: Automatically halts recognition during playback with a 1.2s reverberation guard and text similarity filter to prevent self-listening loops.
- **Dynamic Avatar Lip-Sync**: Audio feeds into a Web Audio `AnalyserNode`, modulating the robot avatar's glowing eyes, mouth-light, and waveform HUD in real time.

### 5. Persistent Long-Term Memory (`memory/`)
- SQLite-backed conversation history and key-value knowledge graph that persists learned hardware configurations, user preferences, and facts across reboots.

---

## System Architecture

```
UnderBot / Cortex
├── cortex/
│   ├── core/
│   │   └── brain.py               # Central ReAct orchestrator & tool execution engine
│   ├── devices/
│   │   └── serial_device.py       # 16-pin Arduino serial bridge with watchdog reconnect
│   ├── firmware/
│   │   └── cortex_nano/
│   │       └── cortex_nano.ino    # Universal dual ASCII & Binary framing Arduino firmware
│   ├── llm/
│   │   ├── agent.py               # Autonomous ReAct agent loop
│   │   ├── client.py              # Ollama API client
│   │   └── tools.py               # OpenAI-compatible function calling schemas
│   ├── memory/
│   │   ├── conversation.py        # SQLite conversation history
│   │   └── knowledge.py           # Persistent key-value knowledge store
│   ├── research/
│   │   └── surfer.py              # Real-time web search and page content extractor
│   ├── tts/
│   │   └── speaker.py             # Edge-TTS neural male voice synthesizer
│   ├── vision/
│   │   ├── camera.py              # Optical emission analysis & Moondream AI vision
│   │   └── probe.py               # Closed-loop automated hardware pin discovery
│   ├── static/                    # Responsive Cyberpunk HUD
│   │   ├── index.html             # Multi-viewport HUD (Camera, Browser, Dual Split)
│   │   ├── css/style.css          # Theme styles, glowing avatar, and search cards
│   │   └── js/
│   │       ├── app.js             # WebSocket coordinator & viewport manager
│   │       ├── face.js            # Expressive robot face animations
│   │       └── voice.js           # Live voice engine with acoustic echo cancellation
│   └── main.py                    # FastAPI server & WebSocket broker
├── backend/                       # Legacy desktop agent & OCR tools
└── README.md                      # Project documentation
```

---

## Hardware Pin Mapping (Arduino Nano)

| Pin Range | Function | Typical Target (e.g. BET RWU Clock Shield) |
| :--- | :--- | :--- |
| `D2` – `D5` | Digital IO | Hours Array (4 Red LEDs) |
| `D6` – `D11` | Digital IO (PWM) | Minutes Array (6 Green LEDs) |
| `D12` – `D13`, `A0` – `A3` | Digital IO | Seconds Array (6 Blue LEDs) |
| `A4` – `A5` | Analog / Digital IO | Push Buttons / Sensor Inputs |
| `USB 5V` | Power Indicator | Onboard Red PWR LED |

---

## Quick Start

### 1. Requirements
- Python 3.11+
- [Ollama](https://ollama.com) with models:
  ```bash
  ollama pull qwen2.5:7b-instruct-q4_K_M
  ollama pull moondream:latest
  ```

### 2. Install Dependencies
```bash
cd cortex
uv pip install -r requirements.txt
uv pip install pyserial opencv-python edge-tts beautifulsoup4
```

### 3. Launch Cortex
```bash
python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## Voice & Interaction Examples

- *"Cortex, find out which pin controls the blue LEDs on my board."*
  *(Cortex switches to camera mode, sequentially tests each pin, checks optical emission changes, and reports the verified pin).*
- *"Cortex, inspect the circuit board and tell me what is illuminated."*
  *(Runs OpenCV optical analysis and Moondream AI to describe exact LED states and board markings).*
- *"Cortex, what are the latest characters released in Genshin Impact?"*
  *(Surfs the live web, parses current guides, and synthesizes up-to-the-minute factual intel).*
- *"Cortex, turn off all LEDs on the Arduino."*
  *(Sets pins D2–D13 and A0–A5 to LOW).*
