"""Launch a local preview. Closing RViz also stops its model publishers."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml
from ament_index_python.packages import get_package_prefix

ROOT = Path(__file__).resolve().parent

def executable(package, name):
    prefix = Path(get_package_prefix(package))
    for folder in (prefix/'lib'/package, prefix/'bin', prefix/'Scripts'):
        for suffix in ('.exe', ''):
            path = folder/(name+suffix)
            if path.is_file():
                return str(path)
    raise FileNotFoundError(f'Cannot find {package}/{name}')

def main():
    # The preview stays on this computer and has no hardware command publishers.
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    os.environ['ROS_DOMAIN_ID'] = '73'
    children=[]
    with tempfile.TemporaryDirectory(prefix='rover-preview-') as temp:
        params=Path(temp)/'robot.yaml'
        params.write_text(yaml.safe_dump({'robot_state_publisher': {'ros__parameters': {
            'robot_description': (ROOT/'rover.urdf').read_text(encoding='utf-8')}}}),encoding='utf-8')
        try:
            children.append(subprocess.Popen([executable('robot_state_publisher','robot_state_publisher'),
                                             '--ros-args','--params-file',str(params)]))
            children.append(subprocess.Popen([executable('joint_state_publisher_gui','joint_state_publisher_gui'),
                                             str(ROOT/'rover.urdf')]))
            rviz=subprocess.Popen([executable('rviz2','rviz2'),'-d',str(ROOT/'rover.rviz')])
            children.append(rviz)
            return rviz.wait()
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
    sys.exit(main())
