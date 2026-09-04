import os
import sys
import asyncio

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from model_manager import ModelManager

async def test_model_manager():
    print("=" * 60)
    print("   Cortex - NEURAL MODEL HUB & AUTO-DOWNLOADER TEST")
    print("   Visual Coder | Multimodal Vision | Deep Automation")
    print("=" * 60)

    mgr = ModelManager()

    # 1. Test Curated Catalog
    print("\n[1/3] Testing Curated Model Catalog...")
    catalog = mgr.CURATED_CATALOG
    assert len(catalog) >= 5
    model_ids = [m["id"] for m in catalog]
    print(f"  [OK] Catalog contains {len(catalog)} specialized models:")
    for m in catalog:
        print(f"       -> {m['name']} ({m['category']}) - {m['size']}")
    assert "qwen2.5-coder:7b" in model_ids
    assert "llava:latest" in model_ids
    assert "deepseek-r1:7b" in model_ids

    # 2. Test Catalog Resolution with Mocked Active Model
    print("\n[2/3] Testing Catalog Status Resolution...")
    cat_status = await mgr.get_catalog_with_status_async(
        api_base="http://localhost:11434/v1",
        active_model="qwen2.5-coder:7b"
    )
    assert "catalog" in cat_status
    assert cat_status["active_model"] == "qwen2.5-coder:7b"
    active_entry = next((c for c in cat_status["catalog"] if c["id"] == "qwen2.5-coder:7b"), None)
    assert active_entry is not None and active_entry["is_active"] == True
    print("  [OK] Successfully resolved catalog state. Active model marked: qwen2.5-coder:7b")

    # 3. Test Progress Listener Dispatch
    print("\n[3/3] Testing Progress Notification Listener Hook...")
    events_received = []
    def on_progress(evt):
        events_received.append(evt)

    mgr.add_listener(on_progress)
    mgr._notify_listeners({
        "model": "qwen2.5-coder:3b",
        "status": "pulling manifest",
        "completed": 500,
        "total": 1000,
        "percent": 50.0,
        "is_done": False
    })

    assert len(events_received) == 1
    assert events_received[0]["percent"] == 50.0
    print(f"  [OK] Progress event captured by listener: {events_received[0]['percent']}% for {events_received[0]['model']}.")

    print("\n" + "=" * 60)
    print("   ALL MODEL MANAGER & AUTO-DOWNLOADER TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_model_manager())
