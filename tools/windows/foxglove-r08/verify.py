from pathlib import Path
import copy
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from install import HERE, SOURCE, DEST, LAYOUTS, IDS

report = json.loads((HERE / 'installation.json').read_text(encoding='utf-8'))
source = ET.parse(SOURCE / 'urdf/underbot.urdf')
installed = ET.parse(DEST / 'urdf/underbot.foxglove.urdf')
assert len(installed.findall('link')) == 23
assert len(installed.findall('joint')) == 22
for original, resource in zip(source.findall('.//mesh'), installed.findall('.//mesh'), strict=True):
    uri = urlparse(resource.attrib['filename'])
    asset = Path(unquote(uri.path).lstrip('/'))
    assert uri.scheme == 'file' and asset.is_file(), asset
    assert asset.read_bytes() == (SOURCE / original.attrib['filename'].removeprefix('package://underbot_description/')).read_bytes()
    resource.set('filename', original.attrib['filename'])
assert ET.tostring(source.getroot()) == ET.tostring(installed.getroot()), 'Unexpected robot geometry change'
for layout_id in IDS:
    original = json.loads((Path(report['backup']) / layout_id).read_text(encoding='utf-8'))
    current = json.loads((LAYOUTS / layout_id).read_text(encoding='utf-8'))
    assert current['baseline'] == original['baseline'], 'Synced baseline changed'
    comparison = copy.deepcopy(current)
    # Opening/inspecting a layout updates view metadata and camera orbit state.
    comparison['lastViewedAt'] = original['lastViewedAt']
    comparison['working']['savedAt'] = original['working']['savedAt']
    for panel_id, panel in current['working']['data']['configById'].items():
        if not panel_id.startswith('3D!'):
            continue
        assert panel['scene']['meshUpAxis'] == 'z_up'
        assert panel['scene']['transforms']['showLabel'] is False
        urdfs = [layer for layer in panel['layers'].values() if layer.get('layerId') == 'foxglove.Urdf']
        assert len(urdfs) == 1 and urdfs[0]['filePath'] == report['model']
        assert urdfs[0]['controlMode'] == 'transforms' and urdfs[0]['visible']
        before = original['working']['data']['configById'][panel_id]
        test_panel = comparison['working']['data']['configById'][panel_id]
        test_panel['cameraState'] = before['cameraState']
        for key in ['layers', 'scene']:
            if key in before:
                test_panel[key] = before[key]
            else:
                test_panel.pop(key, None)
        if layout_id == IDS[-1]:
            assert panel['topics']['/navigation/robot']['visible'] is False
            test_panel['topics']['/navigation/robot'] = before['topics']['/navigation/robot']
    assert comparison == original, f'Unrelated layout changes: {layout_id}'
    print('PASS', current['name'])
print('PASS: all 45 mesh references match source bytes; all 23 links and 22 joints unchanged.')
