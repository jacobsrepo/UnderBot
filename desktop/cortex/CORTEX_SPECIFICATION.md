# Cortex Engine Architecture & Implementation Specification
**Target Platform:** Windows 10/11 | **Host Shell:** Windows PowerShell | **Default Model:** qwen2.5-coder:7b (Ollama)  
**Primary Interfaces:** WebSocket API, Arduino Nano (COM4 @ 115200 Baud), Web Audio API

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 Legacy Vulnerabilities
* **Transitive Hallucination Loops:** Storing full conversational history in an unindexed SQLite table (cortex_memory.db) allowed previous hallucinations to re-enter the model's context window on subsequent turns, causing self-reinforcing fabrication.
* **Temporal Drift:** Absence of ISO-8601 temporal injection at the cycle root forced the LLM to invent timestamps.
* **Synchronous I/O Latency:** Blocking serial transactions, subshell invocations, and synchronous visual inference passes created cumulative turn latencies exceeding 4–8 seconds.
* **Audio Playback Stutter:** Sequential HTML5 <audio> rendering introduced 50–120ms decoding gaps between synthesized sentences.

### 1.2 Architectural Directives
1. **Complete Database Purge:** Terminate and delete all legacy SQLite databases (cortex_memory.db, cortex.db).
2. **OpenClaw Multi-Tier Memory:** Transition to a 3-tier structure consisting of human-editable Markdown (MEMORY.md), timestamped session journals (daily/YYYY-MM-DD.md), and an auto-synchronizing SQLite FTS5 full-text search index.
3. **Pipelined Streaming & Speech:** Stream Ollama tokens immediately to the UI while routing text through a lookahead regex sentence chunker to feed a gapless Web Audio API queue.
4. **Resilient Host Execution:** Enforce Windows PowerShell syntax with command safety blacklists and an automated two-attempt self-healing retry loop.
5. **Threaded Hardware Worker:** Encapsulate serial operations inside a dedicated SerialWorker singleton with queue-based transaction routing and an active watchdog.
