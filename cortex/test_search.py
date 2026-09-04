"""Test the full pipeline: search -> tool result -> what the LLM sees."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import asyncio
import json
from research.surfer import WebSurfer

async def main():
    s = WebSurfer()
    result = await s.surf("latest Genshin Impact characters")
    
    print("=== TITLE:", result.get("title"))
    print("=== URL:", result.get("url"))
    print("=== BADGE:", result.get("badge"))
    print("=== IMAGE:", result.get("image_url"))
    print("=== NUM RESULTS:", len(result.get("results", [])))
    
    for r in result.get("results", [])[:3]:
        print(f"\n  [{r.get('domain')}] {r.get('title')}")
        print(f"    {r.get('snippet', '')[:150]}")
    
    print("\n=== SUMMARY (first 800 chars) ===")
    print(result.get("summary", "")[:800])
    
    # Show what the tool result JSON looks like (what the LLM receives)
    tool_json = json.dumps(result)
    print(f"\n=== TOOL JSON SIZE: {len(tool_json)} bytes ===")

asyncio.run(main())
