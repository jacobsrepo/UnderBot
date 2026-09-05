import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sentence_chunker import SentenceChunker
from memory.openclaw_memory import OpenClawMemory
from cli.runner import PowerShellRunner


def test_openclaw_memory():
    mem = OpenClawMemory(Path("memory"))
    assert mem.memory_file.exists()
    ctx = mem.get_grounding_context()
    assert "Athul" in ctx
    assert "Arduino Nano" in ctx
    hits = mem.search_memory("Arduino")
    assert len(hits) > 0
    mem.append_daily_log("Test Milestone", "Automated diagnostic run passed.")
    daily_files = list(mem.daily_dir.glob("*.md"))
    assert len(daily_files) > 0
    print("test_openclaw_memory PASSED")


def test_sentence_chunker():
    chunker = SentenceChunker(min_char_threshold=5)
    sample = "Hello Athul! The weather in Ravensburg is 18C with 70% humidity. Please check MEMORY.md for more."
    tokens = [t + " " for t in sample.split()]
    extracted = []
    for tok in tokens:
        res = chunker.append(tok)
        if res:
            extracted.extend(res)
    extracted.extend(chunker.flush())
    assert len(extracted) == 3
    print("test_sentence_chunker PASSED")


def test_powershell_safety():
    runner = PowerShellRunner()
    safe, reason = runner._is_safe("Remove-Item -Recurse -Force C:\\")
    assert not safe
    print("test_powershell_safety PASSED")


async def test_powershell_execution():
    runner = PowerShellRunner()
    code, out, err = await runner.execute_raw('Write-Output "Cortex Online"')
    assert code == 0
    assert "Cortex Online" in out
    print("test_powershell_execution PASSED")


if __name__ == "__main__":
    test_openclaw_memory()
    test_sentence_chunker()
    test_powershell_safety()
    asyncio.run(test_powershell_execution())
    print("\nALL SPEC PROTOCOL TESTS PASSED 100%!")
