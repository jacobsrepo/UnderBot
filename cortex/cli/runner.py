"""
Cortex Hardened PowerShell CLI Runner & Self-Healing Loop
Stripped and adapted from OpenClaw's process execution supervisor.
Guarantees native Windows PowerShell execution with $ErrorActionPreference trapping,
parameter aliasing, and an automated 2-attempt self-healing retry loop.
"""

import asyncio
import os
import re
import sys
from typing import Dict, Any, Optional, Tuple, Callable, List


# Parameter & command translation dictionary for common Linux hallucinations
LINUX_TO_POWERSHELL_MAP = [
    (r"\bgrep\b", "Select-String"),
    (r"\bcat\b", "Get-Content"),
    (r"\bls\s+-la\b", "Get-ChildItem -Force"),
    (r"\bls\s+-l\b", "Get-ChildItem"),
    (r"\bls\b", "Get-ChildItem"),
    (r"\btouch\s+([^\s;]+)", r"New-Item -ItemType File -Path \1 -Force"),
    (r"\brm\s+-rf\s+([^\s;]+)", r"Remove-Item -Recurse -Force \1"),
    (r"\brm\s+([^\s;]+)", r"Remove-Item -Force \1"),
    (r"\bmkdir\s+-p\s+([^\s;]+)", r"New-Item -ItemType Directory -Path \1 -Force"),
    (r"\bexport\s+([A-Za-z0-9_]+)=([^\s;]+)", r"$env:\1 = '\2'"),
    (r"\bwhich\s+([^\s;]+)", r"Get-Command \1"),
    (r"\bhead\s+-n\s*(\d+)", r"Select-Object -First \1"),
    (r"\btail\s+-n\s*(\d+)", r"Select-Object -Last \1"),
    (r"\bfind\s+\.\s+-name\s+([^\s;]+)", r"Get-ChildItem -Recurse -Filter \1"),
]


class CliRunner:
    def __init__(self, default_cwd: Optional[str] = None):
        self.default_cwd = default_cwd or os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    def translate_dialect(self, cmd: str) -> str:
        """Translates common Linux/Bash commands into Windows PowerShell cmdlets."""
        translated = cmd
        for pattern, replacement in LINUX_TO_POWERSHELL_MAP:
            translated = re.sub(pattern, replacement, translated)
        return translated

    async def execute_raw(self, command: str, cwd: Optional[str] = None, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Spawns powershell.exe with non-interactive, bypass, and $ErrorActionPreference='Stop'.
        Captures stdout, stderr, and explicit exit codes.
        """
        work_dir = cwd or self.default_cwd
        if not os.path.exists(work_dir):
            work_dir = self.default_cwd

        # Trap non-terminating errors and explicit exit codes
        wrapped_script = (
            "$ErrorActionPreference = 'Stop'; "
            f"try {{ {command} }} catch {{ Write-Error $_.Exception.Message; exit 1 }}; "
            "if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"
        )

        args = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", wrapped_script
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=float(timeout_seconds)
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                return {
                    "success": False,
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                    "timed_out": True
                }

            stdout_text = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr_text = stderr_bytes.decode('utf-8', errors='replace').strip()
            exit_code = process.returncode

            # Trapping: if stderr has content or exit_code != 0, consider as failure
            is_success = (exit_code == 0) and (not stderr_text or "Error" not in stderr_text)

            return {
                "success": is_success,
                "command": command,
                "exit_code": exit_code,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "timed_out": False
            }

        except Exception as e:
            return {
                "success": False,
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Process launch error: {str(e)}",
                "timed_out": False
            }

    async def execute_with_healing(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout_seconds: int = 30,
        healing_agent_cb: Optional[Callable[[str, str], Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a command with dialect translation and up to 2 self-healing retry attempts.
        If a command fails, captures stderr and routes it to healing.
        """
        current_cmd = self.translate_dialect(command)
        attempts = 0
        max_attempts = 3  # Initial + 2 retries
        history_log: List[Dict[str, Any]] = []

        while attempts < max_attempts:
            attempts += 1
            result = await self.execute_raw(current_cmd, cwd, timeout_seconds)
            history_log.append(result)

            if result["success"]:
                return {
                    "success": True,
                    "command": current_cmd,
                    "original_command": command,
                    "exit_code": result["exit_code"],
                    "stdout": result["stdout"],
                    "attempts": attempts,
                    "healed": (attempts > 1)
                }

            # If failed and retries left, self-heal
            if attempts < max_attempts:
                err_msg = result["stderr"] or "Command failed with non-zero exit code."
                print(f"[CliRunner] Attempt {attempts} failed: {err_msg}. Triggering self-healing...")

                # Apply deterministic translation fixes first
                translated_fix = self.translate_dialect(current_cmd)
                if translated_fix != current_cmd:
                    current_cmd = translated_fix
                    continue

                # If an agent callback is provided, request model-guided healing
                if healing_agent_cb:
                    try:
                        healed_cmd = await healing_agent_cb(current_cmd, err_msg)
                        if healed_cmd and healed_cmd.strip():
                            current_cmd = healed_cmd.strip()
                            continue
                    except Exception as e:
                        print(f"[CliRunner] Healing agent failed: {e}")

                # Heuristic healing rules for PowerShell
                if "not recognized as the name of a cmdlet" in err_msg:
                    # Strip linux flags or wrap in cmd /c
                    current_cmd = f"cmd.exe /c {current_cmd}"
                else:
                    break

        # If all retries failed, return detailed context
        last = history_log[-1]
        return {
            "success": False,
            "command": current_cmd,
            "original_command": command,
            "exit_code": last["exit_code"],
            "stdout": last["stdout"],
            "stderr": last["stderr"],
            "attempts": attempts,
            "healed": False
        }
