# UnderBot (Cortex Core) — Autonomous Multimodal Desktop Agent & Cognitive Companion

[![Branch](https://img.shields.io/badge/Branch-Local--VLA--Setup-blue.svg)](https://github.com/jacobsrepo/UnderBot/tree/Local-VLA-Setup)
[![Host Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20Native-0078d4.svg)](#)
[![LLM Engine](https://img.shields.io/badge/LLM-Qwen%202.5%20Coder%207B-orange.svg)](https://ollama.com)
[![Memory Architecture](https://img.shields.io/badge/Memory-OpenClaw%20Dual--Layer-emerald.svg)](#)
[![Maps Engine](https://img.shields.io/badge/Maps-Google%20Maps%20(Zero--Key)-green.svg)](#)
[![Hardware](https://img.shields.io/badge/Hardware-Dynamic%20Serial%20Bridge-cyan.svg)](#)
[![Voice](https://img.shields.io/badge/Voice-Neural%20Male%20(Christopher)-purple.svg)](#)

**UnderBot / Cortex** is a fully local, autonomous multimodal AI companion operating natively on Windows. It combines **real-time browser viewport intelligence**, **zero-key interactive Google Maps**, **pinpoint hardware geolocation**, **closed-loop microcontroller actuation**, **OpenClaw persistent memory**, and **pipelined full-duplex neural voice with an expressive dynamic avatar**.

---

## 🚀 Key Capabilities

### 1. Dynamic Multimodal Browser & Location Engine
- **Authentic Browser Viewport & Omnibar**:
  - Engineered with a genuine browser top-bar featuring navigation controls (Back, Forward, Reload), SSL encryption badge, and direct URL inspection.
  - **Dynamic Context Badges**: Automatically morphs between `DAY BLUEPRINT`, `PRICES & DEALS`, `MAP & PLACES`, and `LIVE INTEL` based on current agent research.
  - Viewports remain persistent across conversation turns for reference without disappearing.
- **Interactive Google Maps (Zero-Key)**:
  - Responsive embedded maps loaded via Google Maps zero-key architecture without requiring paid Google Cloud API keys or quotas.
  - Generates instant navigation links for turn-by-turn directions.
- **Pinpoint Windows Location (Hardware GPS & Wi-Fi Trilateration)**:
  - Bypasses distant ISP/datacenter IP routing via Windows native `.NET System.Device.Location.GeoCoordinateWatcher` combined with high-accuracy browser GPS.
  - Reverse geocodes exact coordinates down to the user's specific street, city, and region via Komoot Photon.
- **1-Day Exploration Blueprint Engine**:
  - Automatically synthesizes 5 chronological schedule blocks (Morning Breakfast, Midday Culture, Lunch, Afternoon Leisure, Evening Dining).
  - Populates authentic venue photography, itemized expenses, budget tiers, local tips, and interactive route preview.
- **Market Price & Deals Comparison**:
  - Resilient multi-tier search engine combining Google Search RSS, Wikipedia OpenSearch, and DuckDuckGo to prevent rate-limiting or connection drops.
  - Parses live prices (`$`, `€`, `£`, `USD`, `EUR`), retailer badges, product thumbnails, and direct store links.
- **Publication-Grade Editorial Reader**:
  - Clean article extraction via Trafilatura with BM25 relevance windowing and breaking news wire alerts.

---

### 2. Autonomous ReAct Agent Loop & Direct Responses
- **Zero Scripted Matching**: Every interaction is dynamically reasoned by `qwen2.5-coder:7b` (via Ollama) executing multi-step tool calls.
- **Direct, Zero-Narration Answers**: Eliminates robotic play-by-play monologue (no *"I will now search PowerShell..."*). The agent executes tools silently in the background and reports concise, definitive results.
- **Mandatory Visual Tool Calling**: Visual, mapping, planning, or price inquiries immediately trigger the browser viewport side-by-side with Cortex's face.

---

### 3. OpenClaw Dual-Layer Memory Architecture
- **Eliminated Transitive Hallucination Loops**: Replaced unindexed conversation databases with a structured, verified root knowledge base (`memory/MEMORY.md`).
- **ISO-8601 Temporal Grounding**: Injects live host timestamps at the root of every cognitive cycle to prevent time fabrications.
- **Daily Journaling**: Appends timestamped audit entries to `daily_journal.jsonl`, maintaining continuous cross-session awareness of projects and preferences.

---

### 4. Hardware Grounding & Arduino Workbench
- **Dynamic Serial Discovery**: Strict USB serial filtering detects genuine microcontrollers on COM ports without false positives from motherboard ACPI ports.
- **Closed-Loop Pin Matrix HUD**: Real-time telemetry monitoring 16 digital and analog IO pins (`D2` through `D13` and `A0` through `A5`).
- **Optical Verification**: Real-time OpenCV optical emission analysis measures actual light wavelengths to verify whether LEDs are physically illuminated.
- **Firmware Pipeline**: Live sketch inspector, one-click pin diagnostics, and interactive Arduino CLI compilation/upload workbench.

---

### 5. Pipelined Neural Voice & Expressive Avatar
- **Pipelined Sentence-by-Sentence TTS**: Audio generation starts immediately on the first recognized sentence chunk while the model continues typing, eliminating turn latency.
- **Authoritative Neural Voice**: Synthesizes natural speech via Microsoft Edge Neural voice (`en-US-ChristopherNeural`).
- **Acoustic Echo Cancellation (AEC)**: Software-managed playback guards and similarity filters prevent the microphone from looping back the assistant's own voice.
- **Dynamic Avatar Lip-Sync**: Real-time Web Audio API `AnalyserNode` drives glowing eyes, mouth-lighting, and audio waveform HUD responsive to speaking intensity.

---

## 🏛️ System Architecture

```
UnderBot / Cortex
├── cortex/
│   ├── core/
│   │   ├── brain.py               # Central ReAct orchestrator, tool dispatcher & stream coordinator
│   │   ├── audio_stream.py        # Sentence chunking & real-time TTS audio pipeline
│   │   └── speech_queue.py        # Asynchronous speech queuing
│   ├── devices/
│   │   ├── serial_device.py       # USB serial bridge with genuine hardware ID filtering
│   │   └── arduino_workbench.py   # Pin state telemetry and firmware compilation runner
│   ├── firmware/
│   │   └── cortex_nano/
│   │       └── cortex_nano.ino    # Dual ASCII / binary framing microcontroller firmware
│   ├── llm/
│   │   ├── agent.py               # Autonomous ReAct agent with textual fallback parser
│   │   ├── client.py              # Low-latency streaming Ollama client
│   │   └── tools.py               # Registered tool specifications & schemas
│   ├── memory/
│   │   ├── MEMORY.md              # OpenClaw verified root grounding & hardware truth
│   │   ├── openclaw_memory.py     # Dual-layer session buffer & daily journal manager
│   │   └── daily_journal.jsonl    # Chronological turn logs & persistent journal
│   ├── research/
│   │   ├── geo.py                 # Windows GeoCoordinateWatcher, Photon POI, Google Maps & Wikipedia media
│   │   └── surfer.py              # Multi-tier web search, 1-day itinerary planner & price comparator
│   ├── skills/
│   │   └── skill_manager.py       # Modular tool and skill catalog manager
│   ├── tts/
│   │   └── speaker.py             # Edge-TTS neural voice synthesizer
│   ├── vision/
│   │   ├── camera.py              # Live webcam streamer & Moondream AI visual analyzer
│   │   └── probe.py               # OpenCV optical ground-truth pin verification
│   ├── static/                    # Responsive Glassmorphic Desktop HUD
│   │   ├── index.html             # Viewports: Dynamic Browser (Omnibar), Camera, Arduino Workbench
│   │   ├── css/style.css          # Glassmorphic cyberpunk styling, radar scanners, timeline cards
│   │   └── js/
│   │       ├── app.js             # WebSocket broker, viewport state coordinator & dynamic view router
│   │       ├── face.js            # Expressive robot face canvas animations
│   │       └── voice.js           # Live voice engine with acoustic echo cancellation
│   └── main.py                    # FastAPI server & WebSocket broker
├── backend/                       # Desktop integration utilities
└── README.md                      # Project documentation
```

---

## ⚡ Quick Start

### 1. Prerequisites
- **Operating System**: Windows 10 or 11 (PowerShell Core / Windows PowerShell)
- **Python**: 3.11+
- **[Ollama](https://ollama.com)** with local models installed:
  ```powershell
  ollama pull qwen2.5-coder:7b
  ollama pull moondream:latest
  ```

### 2. Install Dependencies
```powershell
cd cortex
uv pip install -r requirements.txt
# Alternatively with standard pip:
pip install fastapi uvicorn websockets pyserial opencv-python edge-tts beautifulsoup4 trafilatura
```

### 3. Launch Cortex Server
```powershell
python main.py
```
Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 💬 Example Interactions

- **Location & Google Maps**:
  - *"Where am I located right now?"*  
    *(Pinpoints your physical location via Windows hardware trilateration down to city and street).*
  - *"Show me top-rated specialty coffee shops near me."*  
    *(Opens the browser viewport displaying embedded Google Maps, high-resolution venue photos, ratings, and directions).*

- **Day Planner Blueprint**:
  - *"Plan a 1-day itinerary for exploring Weingarten and Ravensburg."*  
    *(Generates a 5-stop chronological timeline from breakfast to evening dining, itemized budget calculations, route map, and local tips).*

- **Market Prices & Deals**:
  - *"Look up the price of a Raspberry Pi 5."*  
    *(Searches retail channels and displays verified market prices, store badges, and direct links in the browser view).*

- **Hardware Inspection & Physical Agency**:
  - *"Is the Arduino currently plugged in?"*  
    *(Senses physical USB serial devices dynamically and reports genuine connection status).*
  - *"Test all digital pins on the board."*  
    *(Opens the Arduino Workbench HUD and runs sequential pin sweeps).*

---

## 📜 License & Acknowledgments
Built with FastAPI, Ollama, Edge-TTS, OpenStreetMap / Photon, Wikipedia API, and OpenCV. Licensed under MIT.
