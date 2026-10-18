"""Generate Foxglove desktop's import/export layout format (no SDK needed)."""
import json
from pathlib import Path

def split(direction, first, second, percent=50):
    return dict(direction=direction, first=first, second=second, splitPercentage=percent)

def build():
    camera, perception, room, control = 'Image!camera', 'Image!perception', '3D!room', 'robot-station-extension.UnderBot Controls!control'
    data = {
        'configById': {
            camera: {'imageMode': {'imageTopic': '/camera/image/compressed'}, 'title': 'Camera - pan/tilt'},
            perception: {'imageMode': {'imageTopic': '/perception/annotated/compressed'}, 'title': 'Perception - annotated feed'},
            room: {'followTf': 'map', 'cameraState': {'perspective': False, 'distance': 8, 'phi': 0, 'thetaOffset': 0, 'targetOffset': [0,0,0]}, 'topics': {t: {'visible': True} for t in ['/map','/plan','/odom','/scan']}, 'title': 'Room map + planned path'},
            control: {'prefix': '/station', 'lateral': False},
        },
        'globalVariables': {}, 'userNodes': {}, 'linkedGlobalVariables': [], 'playbackConfig': {'speed': 1},
        'layout': split('row', split('column', split('row',camera,perception),room,42),control,68),
    }
    Path(__file__).with_name('underbot-station.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
if __name__ == '__main__':
    build()
