"""Portable supervisor for the station bridge, gateway and optional fake sensors."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from ament_index_python.packages import get_package_prefix

ROOT=Path(__file__).resolve().parent

def executable(package, name):
    prefix=Path(get_package_prefix(package))
    for folder in (prefix/'lib'/package,prefix/'bin',prefix/'Scripts'):
        for suffix in ('.exe',''):
            candidate=folder/(name+suffix)
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError(f'{package}/{name} is not installed')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--navigation-demo',action='store_true')
    parser.add_argument('--address',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--ai-url', default='')
    parser.add_argument('--ai-model', default='qwen2.5:1.5b')
    parser.add_argument('--memory-python', default='')
    parser.add_argument('--memory-config', default='')
    args=parser.parse_args()
    if args.navigation_demo and not args.demo:
        parser.error('--navigation-demo requires --demo')
    if os.name == 'nt':
        # RoboStack ships the Foxglove SDK DLLs in Library/lib rather than bin.
        bridge_prefix = Path(get_package_prefix('foxglove_bridge'))
        os.environ['PATH'] = str(bridge_prefix/'lib') + os.pathsep + os.environ.get('PATH','')
    if args.demo:
        os.environ['ROS_DOMAIN_ID']='74'
        os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
        if os.name == 'nt':
            os.environ.setdefault('RMW_IMPLEMENTATION','rmw_cyclonedds_cpp')
            os.environ.setdefault('CYCLONEDDS_URI','<CycloneDDS><Domain><General><Interfaces><NetworkInterface address="127.0.0.1"/></Interfaces><AllowMulticast>false</AllowMulticast></General></Domain></CycloneDDS>')
    commands=[
        [executable('foxglove_bridge','foxglove_bridge'),'--ros-args','--params-file',str(ROOT/'bridge.yaml'),'-p',f'address:={args.address}','-p',f'port:={args.port}'],
        [sys.executable,str(ROOT/'gateway.py'),'--ros-args','-p',f'mode:={"demo" if args.demo else "live"}'],
    ]
    if args.demo:
        commands.append([sys.executable,str(ROOT/('navigation_demo.py' if args.navigation_demo else 'demo.py'))])
    if args.ai_url:
        commands[1].extend(['-p', f'ai_url:={args.ai_url}', '-p', f'ai_model:={args.ai_model}'])
    if args.memory_python and args.memory_config:
        commands[1].extend(['-p', f'memory_python:={args.memory_python}', '-p', f'memory_config:={args.memory_config}'])
    children=[]
    signal.signal(signal.SIGTERM,lambda *_: sys.exit(0))
    try:
        for command in commands:
            children.append(subprocess.Popen(command))
        while True:
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(f'Station process exited with {child.returncode}')
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

if __name__=='__main__':
    main()
