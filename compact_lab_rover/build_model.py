"""Generate an approximate, visual-only URDF from the supplied concept image."""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
robot = ET.Element('robot', name='compact_lab_rover')
COLORS = {'silver':'0.72 0.76 0.79 1', 'dark':'0.055 0.07 0.085 1',
                   'blue':'0.025 0.32 0.49 1', 'rubber':'0.025 0.03 0.035 1',
                   'glass':'0.03 0.12 0.17 1', 'red':'0.85 0.035 0.02 1',
                   'green':'0.12 0.95 0.22 1', 'yellow':'0.98 0.7 0.02 1'}
for name, rgba in COLORS.items():
    ET.SubElement(ET.SubElement(robot, 'material', name=name), 'color', rgba=rgba)

def link(name):
    return ET.SubElement(robot, 'link', name=name)

def visual(node, kind, size, xyz='0 0 0', rpy='0 0 0', color='silver'):
    v = ET.SubElement(node, 'visual', name=f'{node.attrib["name"]}_visual_{len(node)}')
    ET.SubElement(v, 'origin', xyz=xyz, rpy=rpy)
    g = ET.SubElement(v, 'geometry')
    if kind == 'box':
        ET.SubElement(g, 'box', size=size)
    elif kind == 'cylinder':
        radius, length = size.split()
        ET.SubElement(g, 'cylinder', radius=radius, length=length)
    ET.SubElement(ET.SubElement(v, 'material', name=color), 'color', rgba=COLORS[color])

def joint(name, parent, child, xyz, kind='fixed', axis='0 0 1', limits=(-1.5,1.5)):
    j = ET.SubElement(robot, 'joint', name=name, type=kind)
    ET.SubElement(j, 'parent', link=parent)
    ET.SubElement(j, 'child', link=child)
    ET.SubElement(j, 'origin', xyz=xyz)
    if kind != 'fixed':
        ET.SubElement(j, 'axis', xyz=axis)
        if kind != 'continuous':
            ET.SubElement(j, 'limit', lower=str(limits[0]), upper=str(limits[1]), effort='1', velocity='1')

base=link('base_link')
visual(base,'box','0.20 0.20 0.055','0 0 0.055',color='dark')
body=link('chassis')
joint('chassis_mount','base_link','chassis','0 0 0.0825')
visual(body,'box','0.18 0.18 0.24','0 0 0.12')
for x in (-0.09,0.09):
    for y in (-0.09,0.09):
        visual(body,'box','0.014 0.014 0.245',f'{x} {y} 0.12',color='dark')
visual(body,'box','0.184 0.184 0.007','0 0 0.245',color='dark')
# Front is +X. Front access panel and status bar.
visual(body,'box','0.004 0.125 0.12','0.092 0 0.11',color='blue')
visual(body,'box','0.006 0.012 0.042','0.096 -0.035 0.11',color='dark')
visual(body,'box','0.004 0.07 0.022','0.092 0 0.204',color='dark')
for y in (-0.022,0,0.022):
    visual(body,'cylinder','0.006 0.003',f'0.095 {y} 0.204','0 1.570796 0','glass')
for y,c in ((-0.021,'red'),(0,'yellow'),(0.021,'green')):
    visual(body,'box','0.004 0.019 0.006',f'0.094 {y} 0.231',color=c)
visual(body,'box','0.004 0.12 0.14','-0.092 0 0.10',color='blue')
visual(body,'cylinder','0.014 0.006','-0.095 -0.059 0.204','0 1.570796 0','yellow')
visual(body,'cylinder','0.01 0.012','-0.101 -0.059 0.204','0 1.570796 0','red')
# Four decorative vent fans.
for x in (-0.102,0.102):
    for y in (-0.066,0.066):
        visual(base,'cylinder','0.022 0.005',f'{x} {y} 0.055','0 1.570796 0','rubber')
        visual(base,'cylinder','0.007 0.007',f'{x*1.025} {y} 0.055','0 1.570796 0','silver')
# Stylized mecanum wheels, rollers are visual approximations only.
for x,fore in ((0.065,'front'),(-0.065,'rear')):
    for y,side in ((0.091,'left'),(-0.091,'right')):
        name=f'{fore}_{side}_wheel'
        wheel=link(name)
        joint(name+'_joint','base_link',name,f'{x} {y} 0.035','continuous','0 1 0')
        visual(wheel,'cylinder','0.032 0.02',rpy='1.570796 0 0',color='dark')
        for k in range(8):
            a=k*math.pi/4
            visual(wheel,'cylinder','0.006 0.026',f'{0.028*math.cos(a)} 0 {0.028*math.sin(a)}',
                   f'1.570796 {a} 0.65',color='rubber')
# Three arm joints per side plus a simple opening gripper.
for side,s in (('left',1),('right',-1)):
    upper=link(side+'_upper_arm')
    joint(side+'_shoulder','chassis',side+'_upper_arm',f'0 {s*0.116} 0.16','revolute','0 1 0',(-1.3,1.3))
    visual(upper,'cylinder','0.022 0.036',rpy='1.570796 0 0',color='dark')
    visual(upper,'box','0.025 0.024 0.075','0.013 0 -0.045')
    forearm=link(side+'_forearm')
    joint(side+'_elbow',side+'_upper_arm',side+'_forearm','0.026 0 -0.086','revolute','0 1 0',(-1.6,1.6))
    visual(forearm,'cylinder','0.016 0.029',rpy='1.570796 0 0',color='dark')
    visual(forearm,'box','0.063 0.022 0.019','0.035 0 -0.008')
    palm=link(side+'_gripper')
    joint(side+'_wrist',side+'_forearm',side+'_gripper','0.073 0 -0.008','revolute','1 0 0',(-1.57,1.57))
    visual(palm,'box','0.021 0.05 0.019',color='dark')
    for suffix,fs in (('a',1),('b',-1)):
        finger=link(side+'_finger_'+suffix)
        joint(side+'_finger_'+suffix+'_slide',side+'_gripper',side+'_finger_'+suffix,
              f'0.02 {fs*0.014} 0','prismatic',f'0 {fs} 0',(0,0.012))
        visual(finger,'box','0.033 0.006 0.011','0.01 0 0',color='dark')
# Two-axis camera head. Total nominal height is about 395 mm.
pan=link('camera_pan_link')
joint('camera_pan','chassis','camera_pan_link','0 0 0.253','revolute','0 0 1',(-3.14,3.14))
visual(pan,'cylinder','0.017 0.016','0 0 0.008',color='dark')
visual(pan,'box','0.016 0.019 0.022','0 0 0.025',color='dark')
cam=link('camera_link')
joint('camera_tilt','camera_pan_link','camera_link','0 0 0.042','revolute','0 1 0',(-0.8,0.8))
visual(cam,'box','0.029 0.069 0.034',color='dark')
for y in (-0.021,0.021):
    visual(cam,'cylinder','0.011 0.005',f'0.017 {y} 0','0 1.570796 0','glass')
ET.indent(robot)
ET.ElementTree(robot).write(ROOT/'rover.urdf',encoding='utf-8',xml_declaration=True)
print(f'Generated {len(robot.findall("link"))} links and {len(robot.findall("joint"))} joints')
