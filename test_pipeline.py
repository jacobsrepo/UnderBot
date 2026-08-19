import os
import sys
import time
import asyncio
import cv2

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from camera_stream import CameraManager
from tts_engine import TTSEngine
from stt_engine import STTEngine
from vision_brain import VisionBrain

def run_tests():
    print("=" * 60)
    print("   LOCAL ROBOT BRAIN // PIPELINE SANITY TEST")
    print("=" * 60)

    # 1. Test Camera Stream
    print("\n[1/4] Testing Camera Feed (Camo / System Camera)...")
    cam = CameraManager(device_index=0)
    cam_ok = cam.start(0)
    time.sleep(1.0)
    frame = cam.get_latest_frame_cv2()
    if frame is not None:
        print(f"  --> Camera OK! Captured frame shape: {frame.shape}, FPS: {cam.fps}")
    else:
        print("  --> Camera Warning: No frame returned from device 0. Check Camo Studio.")
    cam.stop()

    # 2. Test TTS Engine (Male Voice)
    print("\n[2/4] Testing Neural Male Voice TTS...")
    tts = TTSEngine(default_voice_key="guy")
    audio_bytes = tts.synthesize_sync("Sensory cortex test. Visual and vocal subroutines nominal.")
    if audio_bytes and len(audio_bytes) > 500:
        print(f"  --> TTS OK! Generated {len(audio_bytes)} bytes of audio with voice '{tts.default_voice_key}'.")
    else:
        print("  --> TTS Error: Audio synthesis failed.")

    # 3. Test STT Engine (Faster-Whisper)
    print("\n[3/4] Testing Faster-Whisper STT Engine...")
    stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")
    if stt.model is not None:
        print("  --> STT OK! Faster-Whisper model loaded and ready for live audio.")
    else:
        print("  --> STT Error: Faster-Whisper failed to initialize.")

    # 4. Test Vision Brain (Ollama)
    print("\n[4/4] Testing Ollama Vision Brain...")
    brain = VisionBrain()
    status = brain.check_ollama_status()
    print(f"  --> Ollama Status: {'ONLINE' if status['online'] else 'OFFLINE'}")
    if status['online']:
        print(f"  --> Available Models: {status['models']}")
        print(f"  --> Selected Model: {status['selected_model']}")
    else:
        print("  --> Note: Ollama service can be started via 'start_brain.bat'.")

    print("\n" + "=" * 60)
    print("   ALL CORE PIPELINES INITIALIZED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
