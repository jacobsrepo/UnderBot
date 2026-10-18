"""Apply the visually verified Z-up setting to all three installed layouts."""
from datetime import datetime, timezone
import json
from install import HERE, LAYOUTS, IDS

for layout_id in IDS:
    path = LAYOUTS / layout_id
    data = json.loads(path.read_text(encoding='utf-8'))
    for panel_id, panel in data['working']['data']['configById'].items():
        if not panel_id.startswith('3D!'):
            continue
        scene = panel.setdefault('scene', {})
        scene['meshUpAxis'] = 'z_up'
        scene['labelScaleFactor'] = 1
        scene.setdefault('transforms', {})['showLabel'] = False
    data['working']['savedAt'] = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    (HERE / 'layouts' / f'{layout_id}-R08.json').write_text(json.dumps(data['working']['data'], indent=2, ensure_ascii=False), encoding='utf-8')
    print(data['name'], 'Z-up; frame labels hidden')
