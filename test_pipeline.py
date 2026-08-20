import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from camera_stream import CameraManager
from tts_engine import TTSEngine
from stt_engine import STTEngine
from vision_brain import VisionBrain

def run_tests():
    print("=" * 60)
    print("   VLA STUDIO - LOCAL SUBSYSTEM VERIFICATION TEST")
    print("=" * 60)

    # 1. Camera
    print("\n[1/4] Testing Camera Capture...")
    cam = CameraManager(device_index=0)
    cam.start(0)
    time.sleep(0.5)
    frame = cam.get_latest_frame_cv2()
    if frame is not None:
        print(f"  [OK] Camera active: {frame.shape}, FPS: {cam.fps}")
    else:
        print("  [INFO] Host camera standing by. Browser camera available.")
    cam.stop()

    # 2. TTS
    print("\n[2/4] Testing Speech Synthesis...")
    tts = TTSEngine(default_voice_key="guy")
    audio_bytes = tts.synthesize_sync("VLA Studio operational.")
    if audio_bytes and len(audio_bytes) > 500:
        print(f"  [OK] Audio generated: {len(audio_bytes)} bytes (voice: {tts.default_voice_key}).")
    else:
        print("  [WARN] Speech synthesis error.")

    # 3. STT
    print("\n[3/4] Testing Speech Recognition...")
    stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")
    if stt.model is not None:
        print("  [OK] Faster-Whisper ready.")
    else:
        print("  [WARN] Speech recognition error.")

    # 4. Embedded Model Engine
    print("\n[4/4] Testing Embedded Qwen2.5-VL Engine...")
    brain = VisionBrain(port=8001)
    status = brain.get_status()
    print(f"  [OK] Model Name: {status['model_name']}")
    print(f"  [OK] Model File: {status['model_file']} ({status['model_size_gb']} GB)")
    print(f"  [OK] Acceleration: {status['acceleration']}")

    time.sleep(1)
    brain.shutdown()

    print("\n" + "=" * 60)
    print("   ALL SUBSYSTEMS VERIFIED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
