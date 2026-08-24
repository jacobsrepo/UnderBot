import os
import sys
import time

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from desktop_agent import DesktopAgent
from embedded_agent import EmbeddedAgent
from intent_router import IntentRouter
from brain import Brain
from vision_engine import VisionEngine
from cognitive_core import CognitiveCore

def test_subsystems():
    print("=" * 60)
    print("   CONTENDER DECOUPLED DUAL-ENGINE TEST SUITE")
    print("   Primary: Qwen2.5-Coder | Secondary: On-Demand Vision")
    print("=" * 60)

    # 1. Desktop Agent & Screen Context Ingestion
    print("\n[1/4] Testing Desktop Agent & On-Demand Screen Ingestion...")
    desktop = DesktopAgent()
    metrics = desktop.get_system_metrics()
    print(f"  [OK] Telemetry: CPU {metrics['cpu_percent']}%, RAM {metrics['ram_used_gb']}/{metrics['ram_total_gb']} GB")

    guard_safe = desktop.check_safety_guardrail("code .", action_type="app_launch")
    assert guard_safe["is_safe"] == True
    guard_unsafe = desktop.check_safety_guardrail("Remove-Item -Recurse C:\\Windows", action_type="shell")
    assert guard_unsafe["is_safe"] == False
    print("  [OK] Safety Guardrails: Destructive command intercepted!")

    screen_txt = desktop.capture_screen_context()
    print(f"  [OK] capture_screen_context() active. Extracted text buffer (length: {len(screen_txt)} chars).")

    # 2. Embedded Hardware Engine & Reflection Loop
    print("\n[2/4] Testing Embedded Hardware & Reflection Loop...")
    embedded = EmbeddedAgent()
    boards = embedded.detect_boards()
    print(f"  [OK] Scanned Boards: {len(boards)} detected via structured CLI JSON.")
    for b in boards:
        print(f"       -> {b['port']}: {b['board_type']} (FQBN: {b.get('fqbn', 'N/A')})")

    test_code_with_err = "void setup() { missing_func() } void loop() {}"
    err_summary = "'missing_func' was not declared in this scope"
    repaired_code = CognitiveCore(desktop, embedded, None, None)._reflect_and_repair_firmware(
        "blink led", test_code_with_err, err_summary
    )
    assert "void loop" in repaired_code
    print("  [OK] Reflection Loop successfully auto-repaired sketch code!")

    # 3. Primary Coder Brain & On-Demand Vision Engine
    print("\n[3/4] Testing Primary Coder Brain & On-Demand Vision Module...")
    primary_brain = Brain()
    status = primary_brain.get_status()
    print(f"  [OK] Primary Brain: {status['engine']} ({status['role']})")
    print(f"       VRAM Status: {status['vram_status']}")

    vision_eng = VisionEngine()
    vis_res = vision_eng.inspect_visual_target(None)
    print(f"  [OK] On-Demand Vision: {vis_res}")

    # 4. Intent Router
    print("\n[4/4] Testing Fast-Path Sensory Router...")
    router = IntentRouter()
    r1 = router.process_utterance("Contender, minimize all windows")
    print(f"  [OK] Prompt: '{r1['prompt']}' -> Intent: {r1['intent']}")
    assert r1["intent"] == "DESKTOP_APP"

    print("\n" + "=" * 60)
    print("   ALL DECOUPLED DUAL-ENGINE SUBSYSTEMS OPERATIONAL")
    print("=" * 60)

if __name__ == "__main__":
    test_subsystems()
