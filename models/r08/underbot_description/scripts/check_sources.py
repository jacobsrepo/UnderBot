"""Check source syntax, Xacro round-trip, resource and actuation consistency.

Requires Python 3 and xacro. Does not run ROS, FreeCAD or a simulator.
"""
from pathlib import Path
import ast, hashlib, json, xml.etree.ElementTree as ET
import xacro

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation'
errors=[]
def check(condition,message):
    if not condition:errors.append(message)
def signature(element):
    return (element.tag,tuple(sorted(element.attrib.items())),(element.text or '').strip(),tuple(signature(c) for c in element if isinstance(c.tag,str)))
def entities(root):
    return {(e.tag,e.get('name')):signature(e) for e in root if e.tag in ('link','joint')}
syntax_files=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'launch').glob('*.py'))+list((ROOT/'cad').glob('*.FCMacro'))
for p in syntax_files:
    try:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    except SyntaxError as e:errors.append(str(e))
source=ROOT/'urdf/underbot.urdf'
core=ET.parse(source).getroot()
portable=ET.parse(ROOT/'urdf/underbot.portable.urdf').getroot()
expanded=xacro.process_file(str(ROOT/'urdf/underbot.urdf.xacro')).toxml()
(OUT/'xacro_expanded.urdf').write_text(expanded,encoding='utf-8')
check(entities(core)==entities(ET.fromstring(expanded)),'Expanded Xacro differs from the authored link/joint model')
for robot in (core,portable,ET.parse(ROOT/'urdf/underbot.gazebo.urdf').getroot()):
    for m in robot.findall('.//mesh'):
        path=m.get('filename')
        asset=ROOT/path.removeprefix('package://underbot_description/') if path.startswith('package://underbot_description/') else ROOT/'urdf'/path
        check(asset.is_file(),f'Missing mesh: {path}')
        check(m.get('scale','1 1 1')=='1 1 1',f'Unexpected mesh scale: {path}')
normalized=ET.fromstring(ET.tostring(portable))
for mesh in normalized.findall('.//mesh'):
    asset=(ROOT/'urdf'/mesh.get('filename')).resolve()
    mesh.set('filename','package://underbot_description/'+asset.relative_to(ROOT).as_posix())
check(entities(core)==entities(normalized),'Package and portable URDF physical descriptions differ')
gazebo=ET.parse(ROOT/'urdf/underbot.gazebo.urdf').getroot()
for mesh in gazebo.findall('.//mesh'):
    asset=(ROOT/'urdf'/mesh.get('filename')).resolve()
    mesh.set('filename','package://underbot_description/'+asset.relative_to(ROOT).as_posix())
check(entities(core)==entities(gazebo),'Gazebo wrapper changed the core physical model')
actuation=json.loads((ROOT/'config/actuation.json').read_text())
joints={j.get('name'):j for j in core.findall('joint')}
commanded={v['name'] for v in actuation['commanded_joints']}
passive=set(actuation['passive_joints'])
followers={v['name'] for v in actuation['mimic_followers']}
moving={n for n,j in joints.items() if j.get('type')!='fixed'}
check(len(commanded)==14 and len(passive)==2 and len(followers)==2,'Incorrect actuation counts')
check(commanded.isdisjoint(passive|followers) and passive.isdisjoint(followers),'Actuation categories overlap')
check(commanded|passive|followers==moving,'Actuation map omits or adds moving joints')
for n in followers:check(joints[n].find('mimic') is not None,f'Follower missing mimic relation: {n}')
for n in passive:check(n.startswith('caster_'),f'Unexpected passive coordinate: {n}')
ET.parse(ROOT/'package.xml')
report={'status':'FAIL' if errors else 'PASS','errors':errors,
    'urdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'checks':['Python and FreeCAD macro syntax only','Xacro semantic round-trip','ROS/portable/Gazebo link and joint equivalence',
              'Mesh resolution and metric scale in all3URDF profiles','14commands/2passive/2mimic actuation map','Package XML parsing'],
    'syntax_files':len(syntax_files),'links':len(core.findall('link')),'joints':len(joints),
    'native_applications_executed':False}
(OUT/'xacro_check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(bool(errors))
