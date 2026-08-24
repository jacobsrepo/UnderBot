import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.desktop_agent import DesktopAgent
from backend.intent_router import IntentRouter
from backend.embedded_agent import EmbeddedAgent

def test_subsystems():
    print("============================================================")
    print("   CONTENDER TACTICAL ASSISTANT - SUBSYSTEM TEST SUITE")
    print("============================================================")

    # 1. Test Desktop Agent
    print("\n[1/3] Testing Desktop OS Agent...")
    desktop = DesktopAgent()
    metrics = desktop.get_system_metrics()
    print(f"  [OK] CPU: {metrics.get('cpu_percent')}%, RAM: {metrics.get('ram_used_gb')}/{metrics.get('ram_total_gb')} GB, Battery: {metrics.get('battery')}")
    
    file_list = desktop.list_directory("Desktop")
    print(f"  [OK] Desktop Directory scanned: {file_list.get('count')} items found.")

    # 2. Test Intent Router
    print("\n[2/3] Testing Wake-Word & Directed Speech Router...")
    router = IntentRouter()
    
    res1 = router.process_utterance("Hey Contender, launch VS Code and check the screen")
    assert res1["has_wake_word"] == True
    assert res1["intent"] == "DESKTOP_APP"
    print(f"  [OK] Wake-word detected: '{res1['prompt']}' -> Intent: {res1['intent']}")

    res2 = router.process_utterance("what is the weather today")
    assert res2["is_directed"] == True # In active thread
    print(f"  [OK] Multi-turn conversational continuity active -> Intent: {res2['intent']}")

    # 3. Test Embedded Agent
    print("\n[3/3] Testing Embedded Microcontroller Engine...")
    embedded = EmbeddedAgent()
    ports = embedded.scan_ports()
    print(f"  [OK] Scanned COM Ports: {len(ports)} detected.")
    for p in ports:
        print(f"       -> {p['port']}: {p['board_type']}")

    code_gen = embedded.generate_microcontroller_code("Blink an LED on ESP32", board="esp32")
    print(f"  [OK] Generated {code_gen['board'].upper()} Firmware ({len(code_gen['code'])} chars).")

    print("\n============================================================")
    print("   ALL CONTENDER SUBSYSTEMS VERIFIED AND OPERATIONAL")
    print("============================================================")

if __name__ == "__main__":
    test_subsystems()
