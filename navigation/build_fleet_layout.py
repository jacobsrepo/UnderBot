"""Generate the paired-URDF view without changing the single-robot layout."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
layout = json.loads((root/'underbot-navigation-layout.json').read_text())
room = layout['configById']['3D!room']
room['title'] = 'Two robots - coordinated navigation simulation'
room['cameraState'].update(distance=7, targetOffset=[0, 0, 0])
room.setdefault('scene', {}).setdefault('transforms', {})['showLabel'] = False
room['scene']['meshUpAxis'] = 'z_up'
room['layers'] = {}
room['topics']['/navigation/team/labels'] = {'visible': True}
for i, color in ((1, '#22ccee'), (2, '#ff9933')):
    name = f'robot_{i}'
    room['layers'][name] = dict(visible=True, frameLocked=True, label=f'Robot {i}',
        instanceId=name, layerId='foxglove.Urdf', sourceType='topic',
        topic=f'/navigation/{name}/robot_description', framePrefix='',
        controlMode='transforms', displayMode='visual', fallbackColor=color, order=i,
        opacity=1, showAxis=False, showOutlines=False, links={})
    room['topics'][f'/navigation/{name}/plan'] = dict(visible=True, color=color, lineWidth=.06)
for topic in ('/navigation/robot', '/plan', '/odom', '/navigation/goal'):
    room['topics'][topic] = {'visible': False}
room['publish'].update(poseTopic='/station/nav/robot_1/goal', goalTopic='/station/nav/robot_1/goal')
room['publish']['type'] = 'pose'
(root/'underbot-fleet-layout.json').write_text(json.dumps(layout, indent=2)+'\n')
print('Generated underbot-fleet-layout.json')
