"""Namespaced URDF instances, zero-joint transforms and conservative planar bounds."""
import math
import xml.etree.ElementTree as ET
import numpy as np


def load_robot(path, prefix):
    tree = ET.parse(path)
    robot = tree.getroot()
    links = {e.attrib['name']: e for e in robot.findall('link')}
    children = {j.find('child').attrib['link'] for j in robot.findall('joint')}
    roots = set(links)-children
    if len(roots) != 1:
        raise ValueError('URDF must have one root link.')
    root = roots.pop()
    transforms = []
    poses = {root: np.eye(4)}

    def pose(element):
        origin = element.find('origin')
        xyz = [float(v) for v in origin.get('xyz', '0 0 0').split()] if origin is not None else [0., 0., 0.]
        r, p, y = [float(v) for v in origin.get('rpy', '0 0 0').split()] if origin is not None else [0., 0., 0.]
        cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
        matrix = np.eye(4)
        matrix[:3, :3] = [[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr], [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr], [-sp, cp*sr, cp*cr]]
        matrix[:3, 3] = xyz
        quaternion = (math.sin(r/2)*math.cos(p/2)*math.cos(y/2)-math.cos(r/2)*math.sin(p/2)*math.sin(y/2),
                      math.cos(r/2)*math.sin(p/2)*math.cos(y/2)+math.sin(r/2)*math.cos(p/2)*math.sin(y/2),
                      math.cos(r/2)*math.cos(p/2)*math.sin(y/2)-math.sin(r/2)*math.sin(p/2)*math.cos(y/2),
                      math.cos(r/2)*math.cos(p/2)*math.cos(y/2)+math.sin(r/2)*math.sin(p/2)*math.sin(y/2))
        return matrix, xyz, quaternion

    pending = list(robot.findall('joint'))
    while pending:
        progress = False
        for joint in pending[:]:
            parent, child = joint.find('parent').get('link'), joint.find('child').get('link')
            if parent not in poses:
                continue
            matrix, xyz, quat = pose(joint)
            poses[child] = poses[parent] @ matrix
            transforms.append((prefix+'/'+parent, prefix+'/'+child, xyz, quat))
            pending.remove(joint); progress = True
        if not progress:
            raise ValueError('URDF joint tree is disconnected or cyclic.')
    radius = .01
    for name, link in links.items():
        for visual in list(link.findall('visual')) + list(link.findall('collision')):
            geometry = visual.find('geometry')
            if geometry is None or len(geometry) != 1:
                raise ValueError('URDF geometry is missing.')
            shape = geometry[0]
            if shape.tag == 'box':
                bound = np.linalg.norm([float(v)/2 for v in shape.get('size').split()])
            elif shape.tag == 'sphere':
                bound = float(shape.get('radius'))
            elif shape.tag == 'cylinder':
                bound = math.hypot(float(shape.get('radius')), float(shape.get('length'))/2)
            else:
                raise ValueError('Fleet demo currently requires primitive URDF geometry (box, sphere, cylinder).')
            centre = (poses[name] @ pose(visual)[0])[:2, 3]
            radius = max(radius, float(np.linalg.norm(centre))+bound)
    for link in robot.findall('link'):
        link.set('name', prefix+'/'+link.get('name'))
    for joint in robot.findall('joint'):
        joint.set('name', prefix+'/'+joint.get('name'))
        for tag in ('parent', 'child'):
            node = joint.find(tag); node.set('link', prefix+'/'+node.get('link'))
        mimic = joint.find('mimic')
        if mimic is not None:
            mimic.set('joint', prefix+'/'+mimic.get('joint'))
    return ET.tostring(robot, encoding='unicode'), prefix+'/'+root, transforms, radius
