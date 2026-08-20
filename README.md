# 👁️ AURA — Universal Vision & Voice Multimodal Assistant

A flexible, minimalist, professional **Vision-Language-Voice** interface that works seamlessly on **any device** (PC, Mac, Linux, mobile phone, tablet).

---

## ✨ Features

- **🌐 Multi-Camera Flexibility**:
  - **Browser / Mobile Webcam**: Stream directly from your phone or laptop camera over the web via HTML5 WebRTC.
  - **Host / USB Camera**: Auto-detects and switches between any connected camera (Camo Studio, USB webcams, integrated cameras).
- **🧠 Flexible Vision Providers**:
  - **Local Ollama**: Accelerated local inference with `qwen2.5vl:7b`, `qwen2.5vl:3b`, `moondream`, `llama3.2-vision`.
  - **Cloud Vision API**: Connect any OpenAI / Gemini / OpenRouter / Groq multimodal API key directly from Settings.
  - **Universal Offline Mode**: Built-in computer vision analysis (lighting, face/person presence, complexity) with zero external setup.
- **🎙️ Real-time Voice Interaction**:
  - **Faster-Whisper STT**: Hold **Spacebar** or click the mic to talk with low-latency transcription.
  - **Neural Male Voice**: Natural, crisp conversational male voices (*Guy, Christopher, Eric, Ryan*).
- **🎨 Minimalist Professional UI**:
  - Clean, slate-themed dark studio interface with real-time waveform visualizer, edge-to-edge video, and settings modal.

---

## 🚀 Quick Start

### 1. Launch the Assistant
Double-click **`start_brain.bat`** (or run with python):
```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### 2. Open in Browser
- On your computer: **`http://localhost:8000`**
- On your phone or another laptop on the same Wi-Fi: **`http://<your-pc-ip>:8000`**

### 3. How to Use
- **Push-to-Talk**: Hold down **Spacebar** (or the microphone button), ask what the camera sees, and release.
- **Scan Scene**: Click **Scan Scene** for an instant situational briefing.
- **Settings**: Click the **⚙️ Settings** icon in the header to change vision models, enter an API key, or switch voices.
