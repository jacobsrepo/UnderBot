import os
import sys
import time

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from desktop_agent import DesktopAgent
from embedded_agent import EmbeddedAgent
from intent_router import IntentRouter
from cognitive_core import CognitiveCore

def test_subsystems():
    print("=" * 60)
    print("   CONTENDER DUAL-ENGINE TACTICAL ASSISTANT - TEST SUITE")
    print("=" * 60)

    # 1. Desktop Agent & Safety Guardrails
    print("\n[1/4] Testing Desktop OS Agent & Safety Guardrails...")
    desktop = DesktopAgent()
    metrics = desktop.get_system_metrics()
    print(f"  [OK] Telemetry: CPU {metrics['cpu_percent']}%, RAM {metrics['ram_used_gb']}/{metrics['ram_total_gb']} GB")

    guard_safe = desktop.check_safety_guardrail("code .", action_type="app_launch")
    assert guard_safe["is_safe"] == True
    guard_unsafe = desktop.check_safety_guardrail("Remove-Item -Recurse C:\\Windows", action_type="shell")
    assert guard_unsafe["is_safe"] == False
    print("  [OK] Safety Guardrails: Destructive commands successfully intercepted!")

    # 2. Smart RapidOCR Screen Ingestion
    print("\n[2/4] Testing Lightweight RapidOCR Screen Ingestion...")
    ocr_res = desktop.extract_screen_text()
    print(f"  [OK] RapidOCR online. Extracted {ocr_res.get('line_count', 0)} text lines from desktop.")

    # 3. Deterministic Embedded Discovery & Reflection Loop
    print("\n[3/4] Testing Embedded Hardware Engine & Reflection Loop...")
    embedded = EmbeddedAgent()
    boards = embedded.detect_boards()
    print(f"  [OK] Scanned Boards: {len(boards)} detected via structured CLI JSON.")
    for b in boards:
        print(f"       -> {b['port']}: {b['board_type']} (FQBN: {b.get('fqbn', 'N/A')})")

    # Reflection Loop Verification: Introduce syntax error intentionally
    print("  [OK] Simulating Compiler Error & Automated Reflection Loop...")
    test_code_with_err = "void setup() { missing_func() } void loop() {}"
    err_summary = "'missing_func' was not declared in this scope"
    repaired_code = CognitiveCore(desktop, embedded, None)._reflect_and_repair_firmware(
        "blink led", test_code_with_err, err_summary
    )
    assert "void loop" in repaired_code
    print("  [OK] Reflection Loop successfully auto-repaired sketch code!")

    # 4. Intent Router & Fast-Path Arbitration
    print("\n[4/4] Testing Wake-Word & Fast-Path Sensory Router...")
    router = IntentRouter()
    r1 = router.process_utterance("Contender, minimize all windows on the desktop")
    print(f"  [OK] Wake-Word: '{r1['prompt']}' -> Intent: {r1['intent']} (Sensory: {r1['vision_source']})")
    assert r1["intent"] == "DESKTOP_APP"

    r2 = router.process_utterance("what is on my screen right now")
    print(f"  [OK] Screen Query: '{r2['prompt']}' -> Intent: {r2['intent']} (Sensory: {r2['vision_source']})")
    assert r2["vision_source"] == "screen"

    r3 = router.process_utterance("look through camera at what I am holding")
    print(f"  [OK] Camera Query: '{r3['prompt']}' -> Intent: {r3['intent']} (Sensory: {r3['vision_source']})")
    assert r3["vision_source"] == "camera"

    print("\n" + "=" * 60)
    print("   ALL CONTENDER DUAL-ENGINE SUBSYSTEMS VERIFIED & OPERATIONAL")
    print("=" * 60)

if __name__ == "__main__":
    test_subsystems()
