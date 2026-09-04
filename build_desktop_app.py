"""
Cortex Dedicated Desktop Application Packager
Compiles Cortex into a standalone Windows executable using PyInstaller.
"""

import os
import sys
import subprocess
import shutil

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def build_executable():
    print("=" * 60)
    print("   CORTEX - DESKTOP APPLICATION BUILDER")
    print("=" * 60)

    if not check_pyinstaller():
        print("\n[Build] PyInstaller not detected in current environment.")
        print("        To compile standalone .exe, install pyinstaller via:")
        print("        uv pip install pyinstaller (or pip install pyinstaller)")
        print("\n[Build] Generating PyInstaller specification file (Cortex.spec)...")

    # Generate PyInstaller Spec
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
root_dir = r"{_ROOT_DIR}"

added_files = [
    (os.path.join(root_dir, 'frontend'), 'frontend'),
    (os.path.join(root_dir, 'backend'), 'backend'),
    (os.path.join(root_dir, 'bin'), 'bin'),
    (os.path.join(root_dir, 'certs'), 'certs'),
]

a = Analysis(
    [os.path.join(root_dir, 'desktop_shell.py')],
    pathex=[root_dir],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'pydantic',
        'webview',
        'aiohttp',
        'psutil',
        'qrcode',
        'cryptography',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Cortex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    spec_path = os.path.join(_ROOT_DIR, "Cortex.spec")
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)
    print(f"  [OK] Generated '{spec_path}'.")

    if check_pyinstaller():
        print("\n[Build] Compiling standalone Cortex.exe with PyInstaller...")
        res = subprocess.run(["pyinstaller", "--clean", spec_path], cwd=_ROOT_DIR)
        if res.returncode == 0:
            exe_path = os.path.join(_ROOT_DIR, "dist", "Cortex.exe")
            print(f"\n[OK] Build complete! Executable located at:\n     {exe_path}")
        else:
            print("\n[ERROR] PyInstaller compilation encountered an error.")
    else:
        print("\n[Info] Ready to build. Run: pyinstaller Cortex.spec")

if __name__ == "__main__":
    build_executable()
