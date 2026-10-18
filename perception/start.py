"""Run live camera and YOLO together; Ctrl+C releases the camera."""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
STOP = ROOT / '.stop-request'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera-name', default='emeet')
    parser.add_argument('--camera-index', type=int)
    parser.add_argument('--domain', type=int, default=74)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--camera-only', action='store_true')
    parser.add_argument('--memory-config')
    parser.add_argument('--no-memory-sync', action='store_true', help='Use the separately managed sync service')
    args = parser.parse_args()
    STOP.unlink(missing_ok=True)
    camera = [sys.executable, '-u', str(ROOT/'camera_node.py'), '--domain', str(args.domain),
              '--camera-name', args.camera_name]
    if args.camera_index is not None:
        camera.extend(['--camera-index', str(args.camera_index)])
    commands = [camera]
    if (ROOT/'location.local.json').is_file():
        commands.append([sys.executable, '-u', str(ROOT/'manual_location.py'),
                         '--domain', str(args.domain)])
    if not args.camera_only:
        commands.append([sys.executable, '-u', str(ROOT/'yolo_node.py'), '--domain',
                         str(args.domain), '--device', args.device])
    if args.memory_config and not args.camera_only:
        memory_path = str(Path(args.memory_config).resolve())
        commands[-1].extend(['--memory-config', memory_path])
        if not args.no_memory_sync and json.loads(Path(memory_path).read_text(encoding='utf-8-sig')).get('base_dsn'):
            commands.append([sys.executable, '-u', '-m', 'memory.cli', '--config', memory_path, 'sync'])
    children = []
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        for command in commands:
            # Native camera/model crashes otherwise report only a Windows exit code.
            command=command[:1]+['-X','faulthandler']+command[1:]
            children.append(subprocess.Popen(command, cwd=ROOT))
        print('Live EMEET pipeline started. Connect the station bridge on domain '
              f'{args.domain}. Ctrl+C stops capture and inference.', flush=True)
        while True:
            if STOP.exists():
                STOP.unlink()
                print('Stop requested; releasing the camera.', flush=True)
                break
            for index,child in enumerate(children):
                if child.poll() is not None:
                    label=' '.join(commands[index][1:3])
                    raise RuntimeError(f'Perception process {label} exited with {child.returncode}')
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()

if __name__ == '__main__':
    main()
