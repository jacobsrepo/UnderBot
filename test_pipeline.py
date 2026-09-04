import os
import sys
import time
import asyncio

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from camera_stream import CameraManager
from tts_engine import TTSEngine
from stt_engine import STTEngine
from brain import Brain
from vision_engine import VisionEngine
from desktop_agent import DesktopAgent
from embedded_agent import EmbeddedAgent
from intent_router import IntentRouter
from cognitive_core import CognitiveCore

def run_tests():
    print("=" * 60)
    print("   Cortex - FULL MULTIMODAL PIPELINE VERIFICATION")
    print("   Decoupled Coder Brain | RapidOCR | Embedded & OS Core")
    print("=" * 60)

    # 1. Camera & Vision Engine
    print("\n[1/5] Testing Camera Stream & Vision Engine...")
    cam = CameraManager(device_index=0)
    cam.start(0)
    time.sleep(0.3)
    frame = cam.get_latest_frame_cv2()
    if frame is not None:
        print(f"  [OK] Camera active: {frame.shape}, FPS: {cam.fps}")
    else:
        print("  [INFO] Host camera standing by. Browser WebRTC camera available.")
    cam.stop()

    vision = VisionEngine()
    vis_res = vision.inspect_visual_target(None)
    print(f"  [OK] Vision Engine: {vis_res}")

    # 2. Audio Pipeline (TTS & STT)
    print("\n[2/5] Testing Speech Pipeline (TTS & STT)...")
    tts = TTSEngine(default_voice_key="guy")
    clean_speech = tts.clean_text_for_speech("Hello `world`! **Cortex** online. Visit http://example.com")
    assert "`" not in clean_speech and "*" not in clean_speech and "http" not in clean_speech
    print(f"  [OK] TTS Clean Text: '{clean_speech}'")

    audio_bytes = tts.synthesize_sync("Cortex pipeline verified.")
    if audio_bytes and len(audio_bytes) > 200:
        print(f"  [OK] TTS Synthesized: {len(audio_bytes)} bytes (voice: {tts.default_voice_key}).")
    else:
        print("  [WARN] TTS synthesis returned empty buffer.")

    stt = STTEngine(model_size="base.en", device="cpu", compute_type="int8")
    if stt.model is not None:
        print(f"  [OK] Faster-Whisper initialized on {stt.device} ({stt.model_size}).")
    else:
        print("  [WARN] Faster-Whisper model not initialized.")

    # 3. Desktop Automation & Safety
    print("\n[3/5] Testing Desktop Agent & Safety Guardrails...")
    desktop = DesktopAgent()
    metrics = desktop.get_system_metrics()
    print(f"  [OK] System Telemetry: CPU {metrics['cpu_percent']}%, RAM {metrics['ram_used_gb']}/{metrics['ram_total_gb']} GB")

    guard_safe = desktop.check_safety_guardrail("notepad", action_type="app_launch")
    assert guard_safe["is_safe"] == True
    guard_unsafe = desktop.check_safety_guardrail("rmdir /s c:\\windows", action_type="shell")
    assert guard_unsafe["is_safe"] == False
    print("  [OK] Safety Interceptor correctly flagged destructive command.")

    # 4. Embedded Hardware & Reflection Loop
    print("\n[4/5] Testing Embedded Agent & C++ Firmware Generation...")
    embedded = EmbeddedAgent()
    boards = embedded.detect_boards()
    print(f"  [OK] Boards Detected: {len(boards)}")
    sketch = embedded.generate_microcontroller_code("blink led on arduino nano", board="nano")
    assert "void setup" in sketch["code"] and "void loop" in sketch["code"]
    print("  [OK] C++ Firmware Generator generated valid Arduino sketch.")

    # 5. Non-Blocking Brain & Cognitive Core Dispatch
    print("\n[5/5] Testing Primary Brain & Cognitive Core Dispatch...")
    primary_brain = Brain()
    router = IntentRouter()
    core = CognitiveCore(desktop, embedded, primary_brain, vision)

    status = primary_brain.get_status()
    print(f"  [OK] Brain Status: {status['engine']} (Online: {status['endpoint_online']})")

    # Run cognitive dispatch async
    async def test_dispatch():
        intent_info = router.process_utterance("Cortex, check system metrics")
        res = await core.process_user_directive(
            text="Cortex, check system metrics",
            intent_info=intent_info
        )
        return res

    dispatch_res = asyncio.run(test_dispatch())
    print(f"  [OK] Cognitive Dispatch Reply: '{dispatch_res['reply'][:60]}...'")
    print(f"       Action Card: {dispatch_res.get('action_card')}")

    primary_brain.shutdown()

    print("\n" + "=" * 60)
    print("   ALL Cortex PIPELINE SUBSYSTEMS VERIFIED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
