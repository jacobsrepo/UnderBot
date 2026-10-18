"""
Cortex Model Manager & Autonomous Model Downloader
Manages AI model catalog, downloads/pulls models from Ollama with real-time streaming,
and provides curated visual coding, robotics, and automation models.
"""

import os
import sys
import json
import asyncio
from typing import Optional, Dict, List, Any, Callable
import aiohttp

class ModelManager:
    """
    Autonomous Model Manager & Stream Downloader.
    Supports auto-downloading chosen visual coding, automation, and vision models.
    """
    CURATED_CATALOG: List[Dict[str, Any]] = [
        {
            "id": "qwen2.5-coder:7b",
            "name": "Qwen2.5-Coder 7B",
            "category": "Visual Coder & Tool Master",
            "badge": "Recommended",
            "size": "4.7 GB",
            "vram": "~5.5 GB VRAM",
            "description": "Primary coding engine. Expert in C++, Arduino, Python, tool dispatch, and visual OCR code repair.",
            "recommended": True
        },
        {
            "id": "qwen2.5-coder:3b",
            "name": "Qwen2.5-Coder 3B",
            "category": "Balanced Visual Coder",
            "badge": "Fast",
            "size": "1.9 GB",
            "vram": "~2.5 GB VRAM",
            "description": "High-speed coding assistant optimized for low VRAM laptops and instant response times.",
            "recommended": False
        },
        {
            "id": "qwen2.5-coder:1.5b",
            "name": "Qwen2.5-Coder 1.5B",
            "category": "Edge Lightweight Coder",
            "badge": "Ultra-Light",
            "size": "1.0 GB",
            "vram": "~1.5 GB VRAM",
            "description": "Featherweight visual coder capable of running entirely on CPU with zero dedicated VRAM.",
            "recommended": False
        },
        {
            "id": "llava:latest",
            "name": "LLaVA 1.6 Visual Core",
            "category": "Multimodal Visual Eyes",
            "badge": "Vision",
            "size": "4.7 GB",
            "vram": "~5.5 GB VRAM",
            "description": "Multimodal vision model for deep physical surroundings inspection, robot schematics, and component detection.",
            "recommended": False
        },
        {
            "id": "deepseek-r1:7b",
            "name": "DeepSeek-R1 7B",
            "category": "Deep Reasoning & Architect",
            "badge": "Reasoning",
            "size": "4.7 GB",
            "vram": "~5.5 GB VRAM",
            "description": "Chain-of-thought reasoning engine for complex multi-step Windows automation workflows.",
            "recommended": False
        },
        {
            "id": "llama3.2:3b",
            "name": "Llama 3.2 3B",
            "category": "Tactical Assistant",
            "badge": "General",
            "size": "2.0 GB",
            "vram": "~2.5 GB VRAM",
            "description": "High-efficiency conversational assistant for natural dialogue and general desktop tasks.",
            "recommended": False
        }
    ]

    def __init__(self, default_api_base: str = "http://localhost:11434/v1"):
        self.default_api_base = default_api_base
        self.active_downloads: Dict[str, Dict[str, Any]] = {}
        self.download_tasks: Dict[str, asyncio.Task] = {}
        self.listeners: List[Callable[[Dict[str, Any]], Any]] = []

    def add_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _get_ollama_base_url(self, api_base: str) -> str:
        """Converts OpenAI-compatible /v1 URL to Ollama native base URL."""
        base = api_base.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        return base

    async def list_installed_models_async(self, api_base: Optional[str] = None) -> List[str]:
        """Queries local Ollama instance for installed models."""
        base_url = self._get_ollama_base_url(api_base or self.default_api_base)
        tags_url = f"{base_url}/api/tags"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(tags_url, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        return [m for m in models if m]
        except Exception:
            pass
        return []

    async def get_catalog_with_status_async(
        self,
        api_base: Optional[str] = None,
        active_model: str = "qwen2.5-coder:7b"
    ) -> Dict[str, Any]:
        """Returns the curated catalog populated with local installation status and download progress."""
        installed = await self.list_installed_models_async(api_base)
        installed_normalized = [m.lower() for m in installed]

        catalog = []
        for item in self.CURATED_CATALOG:
            model_id = item["id"]
            # Check if model id matches installed list (e.g. qwen2.5-coder:7b or qwen2.5-coder:7b-instruct)
            is_installed = any(model_id.lower() in m or m in model_id.lower() for m in installed_normalized)
            is_active = (active_model.lower() == model_id.lower())
            
            download_info = self.active_downloads.get(model_id, None)

            entry = dict(item)
            entry["is_installed"] = is_installed
            entry["is_active"] = is_active
            entry["downloading"] = (download_info is not None and not download_info.get("is_done", False))
            entry["download_progress"] = download_info
            catalog.append(entry)

        # Include custom installed models not in curated list
        custom_installed = []
        for inst in installed:
            if not any(inst.lower() in item["id"].lower() or item["id"].lower() in inst.lower() for item in self.CURATED_CATALOG):
                custom_installed.append({
                    "id": inst,
                    "name": inst,
                    "category": "Custom Local Model",
                    "badge": "Custom",
                    "size": "Local",
                    "vram": "Variable",
                    "description": "Locally installed custom model.",
                    "recommended": False,
                    "is_installed": True,
                    "is_active": (active_model.lower() == inst.lower()),
                    "downloading": False,
                    "download_progress": None
                })

        return {
            "active_model": active_model,
            "catalog": catalog,
            "custom_models": custom_installed,
            "ollama_online": len(installed) > 0 or len(self.active_downloads) > 0
        }

    async def pull_model_stream_async(self, model_name: str, api_base: Optional[str] = None) -> bool:
        """
        Pulls/downloads an AI model from Ollama with real-time streaming progress.
        """
        base_url = self._get_ollama_base_url(api_base or self.default_api_base)
        pull_url = f"{base_url}/api/pull"

        clean_model = model_name.strip()
        if not clean_model:
            return False

        print(f"[ModelManager] Initiating autonomous download for model: '{clean_model}' via {pull_url}...")

        progress_state = {
            "model": clean_model,
            "status": "Starting download...",
            "completed": 0,
            "total": 0,
            "percent": 0.0,
            "is_done": False,
            "error": None
        }
        self.active_downloads[clean_model] = progress_state
        self._notify_listeners(progress_state)

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"name": clean_model, "stream": True}
                async with session.post(pull_url, json=payload, timeout=aiohttp.ClientTimeout(total=3600.0)) as resp:
                    if resp.status != 200:
                        err_msg = f"HTTP {resp.status}: Failed to initiate pull."
                        progress_state["error"] = err_msg
                        progress_state["is_done"] = True
                        self._notify_listeners(progress_state)
                        return False

                    async for line in resp.content:
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line.decode("utf-8").strip())
                            status = chunk.get("status", "")
                            completed = chunk.get("completed", 0)
                            total = chunk.get("total", 0)
                            
                            percent = 0.0
                            if total > 0:
                                percent = round((completed / total) * 100.0, 1)
                            elif "success" in status.lower():
                                percent = 100.0

                            progress_state["status"] = status
                            progress_state["completed"] = completed
                            progress_state["total"] = total
                            progress_state["percent"] = percent

                            if "success" in status.lower() or status == "success":
                                progress_state["is_done"] = True
                                progress_state["percent"] = 100.0
                                print(f"[ModelManager] Download completed successfully for: '{clean_model}'.")
                                self._notify_listeners(progress_state)
                                return True

                            self._notify_listeners(progress_state)
                        except Exception:
                            continue

            progress_state["is_done"] = True
            progress_state["percent"] = 100.0
            self._notify_listeners(progress_state)
            return True

        except Exception as e:
            err_msg = f"Download error: {str(e)}"
            print(f"[ModelManager] Error pulling model '{clean_model}': {err_msg}")
            progress_state["error"] = err_msg
            progress_state["is_done"] = True
            self._notify_listeners(progress_state)
            return False

    def start_pull_task(self, model_name: str, api_base: Optional[str] = None) -> asyncio.Task:
        """Starts a background asyncio task for pulling a model."""
        clean_model = model_name.strip()
        task = asyncio.create_task(self.pull_model_stream_async(clean_model, api_base))
        self.download_tasks[clean_model] = task
        return task

    def get_download_progress(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Returns progress for a specific model or all active downloads."""
        if model_name:
            return self.active_downloads.get(model_name, {
                "model": model_name,
                "status": "Idle",
                "percent": 0.0,
                "is_done": True
            })
        return self.active_downloads

    def _notify_listeners(self, progress_event: Dict[str, Any]):
        for listener in self.listeners:
            try:
                res = listener(progress_event)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass
