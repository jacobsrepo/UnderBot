"""Keep the user's panel arrangement and URDF; select real EMEET image topics."""
import json
from pathlib import Path
from common import IMAGE_TOPIC, ANNOTATED_TOPIC

ROOT = Path(__file__).resolve().parent

def build():
    layout = json.loads((ROOT/'layout-template.json').read_text(encoding='utf-8'))
    changes = {
        '/camera/image/compressed': (IMAGE_TOPIC, 'LIVE EMEET - raw camera'),
        '/perception/annotated/compressed': (ANNOTATED_TOPIC, 'LIVE EMEET - objects + human pose'),
    }
    for panel, config in layout['configById'].items():
        if panel.startswith('Image!'):
            replacement = changes.get(config.get('imageMode', {}).get('imageTopic'))
            if replacement:
                config['imageMode']['imageTopic'], config['title'] = replacement
        layers = config.get('layers', {})
        for layer in (layers.values() if isinstance(layers, dict) else layers):
            if layer.get('filePath') == '__ROVER_URDF__':
                layer['filePath'] = str(ROOT.parent/'compact_lab_rover/rover.urdf')
    output = ROOT/'UnderBot EMEET Live.json'
    output.write_text(json.dumps(layout, indent=2), encoding='utf-8')
    print(f'Import {output} in Foxglove. Original layout is preserved.')

if __name__ == '__main__':
    build()
