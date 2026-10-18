import subprocess
import asyncio
import re
import os
from typing import Tuple, Optional, Callable, Awaitable, Dict, Any


class PowerShellRunner:
    """Safe Windows PowerShell execution harness with a self-healing retry loop."""

    DENY_PATTERNS = [
        re.compile(r"\brmdir\s+/[sS]\b", re.IGNORECASE),
        re.compile(r"\bdel\s+/[sS]\b", re.IGNORECASE),
        re.compile(r"\bFormat-Volume\b", re.IGNORECASE),
        re.compile(r"\bRemove-Item\b.*-Recurse\b.*-Force\b", re.IGNORECASE),
        re.compile(r"\b(?:irm|iex)\b", re.IGNORECASE)
    ]

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def _is_safe(self, command: str) -> Tuple[bool, Optional[str]]:
        for pattern in self.DENY_PATTERNS:
            if pattern.search(command):
                return False, f"Command rejected: matches restricted pattern '{pattern.pattern}'"
        return True, None

    def _auto_quote_paths(self, cmd: str) -> str:
        """Detect unquoted Windows paths containing spaces and wrap them in single quotes."""
        # e.g. C:\Users\Athul C S -> 'C:\Users\Athul C S'
        pattern = r"""(?<!['"])([a-zA-Z]:\\[^"'\n\r;|&<>]*?\s+[^"'\n\r;|&<>]*?)(?=[\s;|&<>]|$)"""
        return re.sub(pattern, r"'\1'", cmd)

    async def execute_raw(self, command: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        safe, reason = self._is_safe(command)
        if not safe:
            return -1, "", reason or "Execution blocked by policy."

        command = self._auto_quote_paths(command)
        wrapped_command = (
            f"$ErrorActionPreference = 'Stop'; "
            f"try {{ {command} }} catch {{ Write-Error $_; exit 1 }}"
        )
        
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", wrapped_command
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), 
                timeout=self.timeout_seconds
            )
            return (
                process.returncode or 0,
                stdout_bytes.decode("utf-8", errors="replace").strip(),
                stderr_bytes.decode("utf-8", errors="replace").strip()
            )
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return -1, "", f"Execution timed out after {self.timeout_seconds} seconds."
        except Exception as e:
            return -1, "", str(e)

    async def run_with_self_healing(
        self, 
        command: str, 
        fix_generator: Optional[Callable[[str, str], Awaitable[str]]] = None,
        cwd: Optional[str] = None
    ) -> Tuple[int, str, str]:
        current_command = command
        max_attempts = 2

        for attempt in range(max_attempts + 1):
            exit_code, stdout, stderr = await self.execute_raw(current_command, cwd=cwd)
            if exit_code == 0:
                return exit_code, stdout, stderr
            
            if attempt < max_attempts and fix_generator:
                current_command = await fix_generator(current_command, stderr)
            else:
                return exit_code, stdout, f"Failed after {max_attempts} corrections. Last error: {stderr}"
                
        return -1, "", "Execution terminated abnormally."

    async def execute_with_healing(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Backward compatibility adapter returning dict for Brain."""
        exit_code, stdout, stderr = await self.execute_raw(command, cwd=cwd)
        if exit_code == 0:
            return {
                "success": True,
                "exit_code": 0,
                "stdout": stdout,
                "stderr": "",
                "command": command,
                "healed": False
            }

        # Quick self-heal for common Bash-isms on Windows
        healed_cmd = command
        if command.startswith("ls "):
            healed_cmd = command.replace("ls ", "Get-ChildItem ", 1)
        elif command.strip() == "ls":
            healed_cmd = "Get-ChildItem"
        elif "cat " in command:
            healed_cmd = command.replace("cat ", "Get-Content ")
        elif "grep " in command:
            healed_cmd = command.replace("grep ", "Select-String -Pattern ")

        if healed_cmd != command:
            h_code, h_out, h_err = await self.execute_raw(healed_cmd, cwd=cwd)
            if h_code == 0:
                return {
                    "success": True,
                    "exit_code": 0,
                    "stdout": h_out,
                    "stderr": "",
                    "command": healed_cmd,
                    "healed": True
                }

        return {
            "success": False,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
            "healed": False
        }


# Alias for backwards compatibility
CliRunner = PowerShellRunner
