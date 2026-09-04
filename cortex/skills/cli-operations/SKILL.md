---
name: CLI Operations
description: Execute native Windows PowerShell commands, automate tasks, inspect files, and query host system state.
tools: run_cli_command
---

# CLI Operations Skill

Use `run_cli_command` to perform real actions on the Windows host machine.

### Dialect Rules:
- Always generate native Windows PowerShell 7 syntax.
- Use `Get-ChildItem` instead of `ls` or `dir`.
- Use `Get-Content` instead of `cat`.
- Use `Select-String` instead of `grep`.
- Use `Get-Date` to inspect exact host system time or calendar.
- Use `Test-Path` to verify file or folder existence.
- The command runner automatically wraps commands with `$ErrorActionPreference = 'Stop'` and traps `$LASTEXITCODE`.
