"""Install an R08 visual model and update only the user's UnderBot URDF layers.

Run with Foxglove closed. Original layouts are backed up before modification.
This does not publish ROS commands or change planner/robot parameters.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
import shutil
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'UnderBot-Personal' / 'underbot_description'
DEST = Path('D:/Robotics/underbot-r08/underbot_description')
LAYOUTS = Path('C:/Users/samja/AppData/Roaming/Foxglove/studio-datastores/layouts-remote-om_0ec7fcCTjGIDJARN')
IDS = ['lay_0ecE6SzApCewruL1', 'lay_0ecFZvmOiK7Rj4wC', 'lay_0eefT2VqM0Z5V2Ra']

def main():
    stamp = datetime.now(timezone.utc)
    backup = HERE / 'backups' / stamp.strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(parents=True)
    exports = HERE / 'layouts'
    exports.mkdir(exist_ok=True)
    for layout_id in IDS:
        shutil.copy2(LAYOUTS / layout_id, backup / layout_id)
    if DEST.exists():
        raise RuntimeError(f'Install destination already exists: {DEST}; inspect it before replacing.')
    shutil.copytree(SOURCE, DEST)
    robot = ET.parse(DEST / 'urdf/underbot.urdf')
    for mesh in robot.findall('.//mesh'):
        path = mesh.attrib['filename']
        prefix = 'package://underbot_description/'
        if not path.startswith(prefix):
            raise ValueError(f'Unexpected mesh reference: {path}')
        resource = DEST / path[len(prefix):]
        if not resource.is_file():
            raise FileNotFoundError(resource)
        mesh.set('filename', resource.as_uri())
    model = DEST / 'urdf/underbot.foxglove.urdf'
    robot.write(model, encoding='utf-8', xml_declaration=True)
    changed = []
    for layout_id in IDS:
        path = LAYOUTS / layout_id
        original = json.loads(path.read_text(encoding='utf-8'))
        layout = copy.deepcopy(original)
        data = layout['working']['data']
        count = 0
        for panel_id, panel in data.get('configById', {}).items():
            if not panel_id.startswith('3D!'):
                continue
            layers = panel.setdefault('layers', {})
            scene = panel.setdefault('scene', {})
            scene['meshUpAxis'] = 'z_up'
            scene['labelScaleFactor'] = 1
            scene.setdefault('transforms', {})['showLabel'] = False
            urdfs = [v for v in layers.values() if v.get('layerId') == 'foxglove.Urdf']
            if not urdfs and layout_id == IDS[-1]:
                instance = str(uuid.uuid4())
                layers[instance] = {'layerId': 'foxglove.Urdf', 'instanceId': instance, 'order': len(layers) + 1}
                urdfs = [layers[instance]]
            for layer in urdfs:
                layer.update({
                    'sourceType': 'filePath', 'filePath': str(model), 'url': '', 'parameter': '', 'topic': '',
                    'label': 'UnderBot R08 - design model', 'controlMode': 'transforms', 'jointStatesTopic': '',
                    'displayMode': 'visual', 'visible': True, 'opacity': 1, 'showAxis': False,
                    'showOutlines': False, 'framePrefix': '', 'links': {},
                })
                count += 1
            if layout_id == IDS[-1]:
                panel.setdefault('topics', {}).setdefault('/navigation/robot', {})['visible'] = False
        if not count:
            raise RuntimeError(f'No URDF layer updated in {layout_id}')
        # Preserve the synced baseline and its revision; these are local working edits.
        layout['working']['savedAt'] = stamp.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        path.write_text(json.dumps(layout, indent=2, ensure_ascii=False), encoding='utf-8')
        (exports / f'{layout_id}-R08.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        changed.append({'id': layout_id, 'name': layout['name'], 'urdf_layers': count})
    report = {'model': str(model), 'backup': str(backup), 'layouts': changed,
              'links': len(robot.findall('link')), 'joints': len(robot.findall('joint')),
              'mesh_references': len(robot.findall('.//mesh')),
              'scope': 'Visualization only. Navigation and ROS publishers unchanged.'}
    (HERE / 'installation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
