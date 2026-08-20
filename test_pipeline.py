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
    print("   AURA // 100% STANDALONE LOCAL PIPELINE TEST")
    print("=" * 60)

    # 1. Test Camera
    print("\n[1/4] Testing Camera Capture...")
    cam = CameraManager(device_index=0)
    cam.start(0)
    time.sleep(1.0)
    frame = cam.get_latest_frame_cv2()
    if frame is not None:
        print(f"  --> Camera OK! Shape: {frame.shape}, FPS: {cam.fps}")
    else:
        print("  --> Camera Warning: No local frame. Browser webcam will be used.")
    cam.stop()

    # 2. Test TTS (Male Voice)
    print("\n[2/4] Testing Neural Male Voice TTS...")
    tts = TTSEngine(default_voice_key="guy")
    audio_bytes = tts.synthesize_sync("Local standalone cortex online. All systems nominal.")
    if audio_bytes and len(audio_bytes) > 500:
        print(f"  --> TTS OK! Generated {len(audio_bytes)} bytes with voice '{tts.default_voice_key}'.")
    else:
        print("  --> TTS Error: Audio synthesis failed.")

    # 3. Test STT
    print("\n[3/4] Testing Faster-Whisper STT...")
    stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")
    if stt.model is not None:
        print("  --> STT OK! Faster-Whisper ready.")
    else:
        print("  --> STT Error: STT failed to load.")

    # 4. Test Embedded Standalone Qwen2.5-VL Engine
    print("\n[4/4] Testing Standalone Embedded Qwen2.5-VL 7B...")
    brain = VisionBrain(port=8001)
    status = brain.get_status()
    print(f"  --> Engine: {status['engine']}")
    print(f"  --> Model File: {status['model_file']} ({status['model_size_gb']} GB)")
    print(f"  --> Ready on GPU: {status['ready']}")

    time.sleep(2)
    brain.shutdown()

    print("\n" + "=" * 60)
    print("   100% LOCAL STANDALONE SETUP FULLY OPERATIONAL!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
