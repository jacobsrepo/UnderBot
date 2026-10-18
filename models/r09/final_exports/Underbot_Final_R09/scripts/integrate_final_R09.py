from pathlib import Path
import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET

workspace = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Integrate detailed SI visual meshes into the accompanying URDF package.')
parser.add_argument('--output', type=Path, default=workspace / 'outputs/Underbot_Final_R09')
out = parser.parse_args().output.resolve()
package = out / 'underbot_description'
export = json.loads((out / 'geometry_export_manifest.json').read_text(encoding='utf-8'))
groups = [record for record in export['grouped_meshes'] if record['units'] == 'm']
assert len(groups) == 45
for record in groups:
    src = out / record['path']
    shutil.copyfile(src, package / 'meshes' / src.name)
    shutil.copyfile(src.with_suffix('.obj'), package / 'meshes' / src.with_suffix('.obj').name)
mtl = (out / 'models/meshes/Underbot_R09.mtl').read_text(encoding='utf-8')
(package / 'meshes/Underbot_R09.mtl').write_text(mtl.replace('../../textures/', '../textures/'), encoding='utf-8')
# OBJ has relative references to packaged textures; standalone extraction and
# ROS installation therefore do not depend on the surrounding final bundle.
(package / 'textures').mkdir(exist_ok=True)
for path in (out / 'textures').glob('*.png'):
    if not path.stem.endswith('_metallicroughness'):
        shutil.copyfile(path, package / 'textures' / path.name)
robot = ET.parse(package / 'urdf/underbot.portable.urdf').getroot()
for visual in robot.findall('link/visual'):
    mesh = visual.find('geometry/mesh')
    mesh.set('filename', str(Path(mesh.get('filename')).with_suffix('.obj')).replace('\\', '/'))
    material = visual.find('material')
    if material is not None:
        visual.remove(material)
ET.indent(robot, space='  ')
(package / 'urdf/underbot.textured.urdf').write_bytes(ET.tostring(robot, encoding='utf-8', xml_declaration=True) + b'\n')
cmake = package / 'CMakeLists.txt'
text = re.sub(r'install\(DIRECTORY urdf meshes launch rviz config docs(?: textures)*',
              'install(DIRECTORY urdf meshes launch rviz config docs textures',
              cmake.read_text(encoding='utf-8'))
cmake.write_text(text, encoding='utf-8')
metadata = package / 'package.xml'
text = metadata.read_text(encoding='utf-8').replace('<version>0.8.0</version>', '<version>0.9.0</version>')
text = text.replace('Underbot R08 WR141E mobile dual-arm model with a 200 mm square tower and bare camera electronics reservation.',
                    'Underbot R09 detailed visual model with 200 mm floors, 204 mm covers, and the tested R08 WR141E physical configuration.')
metadata.write_text(text, encoding='utf-8')
archive = out.parent / (out.name + '_previous_validation')
archive.mkdir(exist_ok=True)
for name in ('pybullet_preview_R08.json', 'pybullet_preview_R08.md', 'viewer_checks_R08.json',
             'delivery_check.json', 'sha256_manifest.json'):
    path = package / 'validation' / name
    if path.exists():
        shutil.copyfile(path, archive / name)
        path.unlink()
print(json.dumps({'integrated_si_stl_meshes': len(groups), 'optional_textured_obj_meshes': len(groups),
                  'core_physics_model': 'Unchanged R08 parameters, collision geometry, joints and inertias',
                  'optional_texture_profile': 'urdf/underbot.textured.urdf'}, indent=2))
