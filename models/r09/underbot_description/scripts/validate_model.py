#!/usr/bin/env python3
"""Independent structural, inertial, mesh and kinematic checks for Underbot.

This is a portable authoring check, not a simulator or certification of real
hardware. Collision checks use exact oriented boxes for box primitives and
conservative oriented bounds for cylinders/meshes. Candidate intersections
therefore require inspection; they are not claimed as proven penetrations.
Requires Python 3 and NumPy; no ROS, Gazebo or Isaac installation is assumed.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np

EPS = 1e-9


def vector(text, count=3, default=None):
    if text is None:
        return np.asarray(default if default is not None else [0.] * count, dtype=float)
    result = np.asarray([float(x) for x in text.split()], dtype=float)
    if result.shape != (count,) or not np.isfinite(result).all():
        raise ValueError(f"Expected {count} finite numbers: {text!r}")
    return result


def rotation(rpy):
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                     [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
                     [-sp, cp*sr, cp*cr]])


def origin(element):
    t = np.eye(4)
    if element is not None:
        t[:3, 3] = vector(element.get('xyz'))
        t[:3, :3] = rotation(vector(element.get('rpy')))
    return t


def axis_rotation(axis, angle):
    x, y, z = axis
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle)*k + (1-math.cos(angle))*(k @ k)


def stl_triangles(path):
    data = path.read_bytes()
    if len(data) >= 84:
        count = struct.unpack_from('<I', data, 80)[0]
        if len(data) == 84 + 50 * count:
            points = []
            for index in range(count):
                values = struct.unpack_from('<12fH', data, 84+50*index)
                points.append(np.array(values[3:12]).reshape(3, 3))
            return np.asarray(points, dtype=float)
    values = []
    for line in data.decode('ascii').splitlines():
        tokens = line.strip().split()
        if tokens and tokens[0].lower() == 'vertex':
            values.append([float(v) for v in tokens[1:]])
    result = np.asarray(values, dtype=float)
    if len(result) % 3:
        raise ValueError('STL vertex count is not a multiple of three')
    return result.reshape(-1, 3, 3)


def inspect_stl(path):
    tris = stl_triangles(path)
    if not len(tris) or tris.shape[1:] != (3, 3) or not np.isfinite(tris).all():
        raise ValueError('STL has no finite valid triangles')
    edges = {}
    oriented = {}
    degenerates = 0
    for a, b, c in tris:
        if np.linalg.norm(np.cross(b-a, c-a)) < 1e-15:
            degenerates += 1
        keys = [tuple(np.round(v, 9)) for v in (a, b, c)]
        for u, v in zip(keys, keys[1:]+keys[:1]):
            edge = tuple(sorted((u, v)))
            edges[edge] = edges.get(edge, 0) + 1
            oriented[edge] = oriented.get(edge, 0) + (1 if u <= v else -1)
    volume = float(np.einsum('ij,ij->i', tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum()/6)
    return {'triangles': len(tris), 'bounds_min': tris.min((0, 1)).tolist(),
            'bounds_max': tris.max((0, 1)).tolist(), 'signed_volume_m3': volume,
            'degenerate_triangles': degenerates,
            'open_or_nonmanifold_edges': sum(v != 2 for v in edges.values()),
            'inconsistently_oriented_edges': sum(v != 0 for v in oriented.values()),
            'closed_oriented_multishell_surface': all(v >= 2 and v % 2 == 0 for v in edges.values()) and all(v == 0 for v in oriented.values()),
            'closed': all(v == 2 for v in edges.values()) and all(v == 0 for v in oriented.values())}


def box_vertices(lo, hi):
    return np.array(list(itertools.product(*zip(lo, hi))))


def transform_points(t, p):
    return p @ t[:3, :3].T + t[:3, 3]


def oriented_box_intersects(a, b, tolerance=1e-5):
    """SAT for OBBs; tangency and overlaps below tolerance are not penetration."""
    ca, ra, ea = a
    cb, rb, eb = b
    if np.any(np.abs(cb-ca) >= np.abs(ra) @ ea+np.abs(rb) @ eb-tolerance):
        return False
    candidates = [*ra.T, *rb.T]
    candidates.extend(np.cross(x, y) for x in ra.T for y in rb.T)
    delta = cb-ca
    for axis in candidates:
        n = np.linalg.norm(axis)
        if n < 1e-8:
            continue
        axis = axis/n
        pa = np.abs(ra.T @ axis) @ ea
        pb = np.abs(rb.T @ axis) @ eb
        if abs(delta @ axis) >= pa+pb-tolerance:
            return False
    return True


class Validator:
    def __init__(self, urdf, expectations, samples):
        self.path = Path(urdf).resolve()
        self.package = self.path.parent.parent
        self.expected = expectations or {}
        self.samples = samples
        self.errors = []
        self.warnings = []
        self.report = {'file': str(self.path), 'units': 'm, kg, rad, kg m^2',
                       'scope': 'Independent Python authoring validation; no simulator import or dynamics run',
                       'limitations': ['Hardware dimensions, masses, motor limits and contact coefficients are not measured by this validator.',
                         'Collision screening uses primitive oriented bounds; cylinder and mesh candidates may be false positives.',
                         'One-joint sweeps do not prove collision freedom for simultaneous multi-joint motion.']}
        self.meshes = {}

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def parse(self):
        self.report['urdf_sha256'] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.robot = ET.parse(self.path).getroot()
        if self.robot.tag != 'robot':
            raise ValueError('Root XML element is not robot')
        link_list = self.robot.findall('link')
        joint_list = self.robot.findall('joint')
        self.links = {v.get('name'): v for v in link_list}
        self.joints = {v.get('name'): v for v in joint_list}
        if len(self.links) != len(link_list) or None in self.links:
            self.error('Link names are missing or duplicated')
        if len(self.joints) != len(joint_list) or None in self.joints:
            self.error('Joint names are missing or duplicated')
        self.parents = {}
        self.children = {name: [] for name in self.links}
        self.joint_data = {}
        for name, j in self.joints.items():
            parent = j.find('parent').get('link')
            child = j.find('child').get('link')
            kind = j.get('type')
            if parent not in self.links or child not in self.links:
                self.error(f'{name}: joint references a missing link')
                continue
            if child in self.parents:
                self.error(f'{child}: multiple parents')
            self.parents[child] = (parent, name)
            self.children[parent].append((child, name))
            t = origin(j.find('origin'))
            axis = vector(j.find('axis').get('xyz') if j.find('axis') is not None else None, default=[1., 0., 0.])
            if kind not in ('fixed', 'revolute', 'continuous', 'prismatic', 'floating', 'planar'):
                self.error(f'{name}: unknown URDF joint type {kind}')
            if kind not in ('fixed', 'floating') and abs(np.linalg.norm(axis)-1) > 1e-6:
                self.error(f'{name}: axis is not a unit vector')
            limits = None
            if kind in ('revolute', 'prismatic', 'continuous'):
                lim = j.find('limit')
                if lim is None:
                    self.error(f'{name}: missing joint limit')
                else:
                    effort = float(lim.get('effort', 'nan'))
                    velocity = float(lim.get('velocity', 'nan'))
                    if not all(math.isfinite(v) and v > 0 for v in (effort, velocity)):
                        self.error(f'{name}: effort/velocity must be finite and positive')
                    if kind != 'continuous':
                        limits = (float(lim.get('lower', 'nan')), float(lim.get('upper', 'nan')))
                        if not all(math.isfinite(v) for v in limits) or limits[0] >= limits[1]:
                            self.error(f'{name}: position limits are invalid')
                for tag in ('dynamics',):
                    node = j.find(tag)
                    if node is not None:
                        for field in ('damping', 'friction'):
                            value = float(node.get(field, '0'))
                            if not math.isfinite(value) or value < 0:
                                self.error(f'{name}: {field} is invalid')
            mimic = j.find('mimic')
            if mimic is not None:
                target = mimic.get('joint')
                if target not in self.joints or target == name:
                    self.error(f'{name}: invalid mimic target')
                for field, default in [('multiplier', '1'), ('offset', '0')]:
                    if not math.isfinite(float(mimic.get(field, default))):
                        self.error(f'{name}: non-finite mimic {field}')
            self.joint_data[name] = {'parent': parent, 'child': child, 'type': kind,
                                     'origin': t, 'axis': axis, 'limits': limits, 'mimic': mimic}
        roots = sorted(set(self.links)-set(self.parents))
        if len(roots) != 1:
            self.error(f'Expected one root link, found {roots}')
        self.root = roots[0] if roots else None
        if self.root:
            seen = set()
            active = set()
            def visit(link):
                if link in active:
                    self.error(f'Cycle at link {link}')
                    return
                active.add(link)
                seen.add(link)
                for child, _ in self.children[link]:
                    if child not in seen:
                        visit(child)
                    elif child in active:
                        self.error(f'Cycle at link {child}')
                active.remove(link)
            visit(self.root)
            if seen != set(self.links):
                self.error('Some links are unreachable from the root')
        types = {kind: sum(j.get('type') == kind for j in joint_list) for kind in sorted({j.get('type') for j in joint_list})}
        independent = sum(j.get('type') != 'fixed' and j.find('mimic') is None for j in joint_list)
        self.report['structure'] = {'name': self.robot.get('name'), 'root': self.root,
            'link_count': len(self.links), 'joint_count': len(self.joints), 'joint_types': types,
            'independent_joint_coordinates': independent}

    def fk(self, positions=None):
        positions = dict(positions or {})
        def position(name, trail=None):
            trail = trail or set()
            if name in trail:
                raise ValueError('Mimic joint cycle')
            trail.add(name)
            info = self.joint_data[name]
            mimic = info['mimic']
            if mimic is not None:
                return position(mimic.get('joint'), trail)*float(mimic.get('multiplier', '1'))+float(mimic.get('offset', '0'))
            return positions.get(name, 0.)
        result = {self.root: np.eye(4)}
        def visit(link):
            for child, name in self.children[link]:
                info = self.joint_data[name]
                m = np.eye(4)
                q = position(name)
                if info['type'] in ('continuous', 'revolute'):
                    m[:3, :3] = axis_rotation(info['axis'], q)
                elif info['type'] == 'prismatic':
                    m[:3, 3] = info['axis']*q
                result[child] = result[link] @ info['origin'] @ m
                visit(child)
        visit(self.root)
        return result

    def mesh_path(self, uri):
        if uri.startswith('package://'):
            package, _, rest = uri[len('package://'):].partition('/')
            if package != 'underbot_description':
                raise ValueError(f'Unresolvable external package {package}')
            return (self.package/rest).resolve()
        if uri.startswith('file://'):
            return Path(uri[7:]).resolve()
        return (self.path.parent/uri).resolve()

    def geometry(self, element, link, kind, index):
        t = origin(element.find('origin'))
        g = element.find('geometry')
        if g is None or len(g) != 1:
            raise ValueError(f'{link} {kind} {index}: requires one geometry')
        shape = g[0]
        shape_type = shape.tag
        exact_box = False
        if shape_type == 'box':
            size = vector(shape.get('size'))
            if np.any(size <= 0):
                raise ValueError('Nonpositive box size')
            lo, hi = -size/2, size/2
            exact_box = True
        elif shape_type == 'cylinder':
            radius, length = float(shape.get('radius')), float(shape.get('length'))
            if min(radius, length) <= 0 or not all(map(math.isfinite, (radius, length))):
                raise ValueError('Invalid cylinder')
            lo, hi = np.array([-radius, -radius, -length/2]), np.array([radius, radius, length/2])
        elif shape_type == 'sphere':
            radius = float(shape.get('radius'))
            if radius <= 0 or not math.isfinite(radius):
                raise ValueError('Invalid sphere')
            lo, hi = np.array([-radius]*3), np.array([radius]*3)
        elif shape_type == 'mesh':
            p = self.mesh_path(shape.get('filename', ''))
            if not p.is_file():
                raise ValueError(f'Missing mesh {p}')
            scale = vector(shape.get('scale'), default=[1., 1., 1.])
            if np.any(scale <= 0):
                raise ValueError('Nonpositive mesh scale')
            if p.suffix.lower() != '.stl':
                self.warn(f'Numeric inspection not available for {p.name}')
                return None
            if str(p) not in self.meshes:
                info = inspect_stl(p)
                self.meshes[str(p)] = info
                if info['degenerate_triangles']:
                    self.error(f'{p.name}: {info["degenerate_triangles"]} degenerate triangles')
                if not info['closed']:
                    if kind == 'visual' and info['closed_oriented_multishell_surface']:
                        self.warn(f'{p.name}: closed oriented visual shells touch at {info["open_or_nonmanifold_edges"]} nonmanifold edges; not a unioned physics solid')
                    else:
                        self.error(f'{p.name}: mesh is not closed and consistently oriented')
                if info['signed_volume_m3'] <= 0:
                    self.error(f'{p.name}: nonpositive signed mesh volume')
            info = self.meshes[str(p)]
            lo, hi = np.array(info['bounds_min'])*scale, np.array(info['bounds_max'])*scale
        else:
            raise ValueError(f'Unsupported geometry {shape_type}')
        if not np.isfinite(lo).all() or not np.isfinite(hi).all():
            raise ValueError('Nonfinite bounds')
        if np.max(hi-lo) > 5:
            self.error(f'{link}: geometry exceeds 5m; check mm-to-m conversion')
        return {'name': element.get('name', f'{kind}_{index}'), 'type': shape_type,
                'origin': t, 'lo': lo, 'hi': hi, 'exact_box': exact_box}

    def inspect_geometry(self):
        self.geometries = {}
        self.world = self.fk()
        world_bounds = {}
        for name, link in self.links.items():
            self.geometries[name] = {'visual': [], 'collision': []}
            for kind in ('visual', 'collision'):
                points = []
                for index, node in enumerate(link.findall(kind)):
                    try:
                        g = self.geometry(node, name, kind, index)
                    except Exception as e:
                        self.error(f'{name} {kind}: {e}')
                        continue
                    if g:
                        self.geometries[name][kind].append(g)
                        points.extend(transform_points(self.world[name] @ g['origin'], box_vertices(g['lo'], g['hi'])))
                if points:
                    points = np.array(points)
                    world_bounds.setdefault(name, {})[kind] = {'min': points.min(0).tolist(), 'max': points.max(0).tolist()}
        self.report['zero_pose_world_bounds'] = world_bounds
        self.report['stl_meshes'] = self.meshes
        for name, expected in self.expected.get('expected_world_bounds', {}).items():
            kind = expected.get('geometry', 'visual')
            value = world_bounds.get(name, {}).get(kind)
            if value is None:
                self.error(f'Expected {kind} bounds absent for {name}')
                continue
            tolerance = expected.get('tolerance', .001)
            for key in ('min', 'max'):
                if key in expected and not np.allclose(value[key], expected[key], atol=tolerance, rtol=0):
                    self.error(f'{name}: world {kind} {key} differs from expected {expected[key]} (actual {value[key]})')

    def inspect_inertias(self):
        total = 0.
        weighted = np.zeros(3)
        bodies = []
        zero_reference_frames = []
        def has_moving_descendant(link):
            return any(self.joint_data[joint]['type'] != 'fixed' or has_moving_descendant(child)
                       for child, joint in self.children[link])
        for name, link in self.links.items():
            node = link.find('inertial')
            dynamic = name in self.parents and self.joints[self.parents[name][1]].get('type') != 'fixed'
            if node is None:
                if dynamic:
                    self.error(f'{name}: moving link has no inertial')
                continue
            try:
                mass = float(node.find('mass').get('value'))
                if not math.isfinite(mass) or mass < 0:
                    raise ValueError('mass must be finite and positive')
                i = node.find('inertia')
                vals = {key: float(i.get(key)) for key in ('ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz')}
                tensor = np.array([[vals['ixx'], vals['ixy'], vals['ixz']],
                                   [vals['ixy'], vals['iyy'], vals['iyz']],
                                   [vals['ixz'], vals['iyz'], vals['izz']]])
                if not np.isfinite(tensor).all():
                    raise ValueError('nonfinite tensor')
                if mass == 0:
                    fixed_connected = name in self.parents and self.joint_data[self.parents[name][1]]['type'] == 'fixed'
                    shape_free = not link.findall('visual') and not link.findall('collision')
                    if not fixed_connected or not shape_free or has_moving_descendant(name):
                        raise ValueError('zero mass is allowed only for shape-free fixed reference frames with no moving descendants')
                    if np.any(tensor != 0):
                        raise ValueError('zero-mass reference frame must have an exactly zero inertia tensor')
                    origin(node.find('origin'))  # still reject nonfinite frame origins
                    zero_reference_frames.append(name)
                    continue
                eigen = np.linalg.eigvalsh(tensor)
                if eigen[0] <= 0:
                    raise ValueError(f'inertia is not positive definite: {eigen.tolist()}')
                if eigen[2] > eigen[0]+eigen[1]+max(1e-12, eigen[2]*1e-8):
                    raise ValueError(f'inertia principal moments violate triangle inequality: {eigen.tolist()}')
                t = self.world[name] @ origin(node.find('origin'))
                center = t[:3, 3]
                world_tensor = t[:3, :3] @ tensor @ t[:3, :3].T
                total += mass
                weighted += mass*center
                bodies.append({'link': name, 'mass_kg': mass, 'world_com_m': center.tolist(),
                               'principal_inertias_kg_m2': eigen.tolist(), 'world_tensor': world_tensor})
            except Exception as e:
                self.error(f'{name}: invalid inertial: {e}')
        center = weighted/total if total else np.zeros(3)
        combined = np.zeros((3, 3))
        for body in bodies:
            d = np.array(body['world_com_m'])-center
            combined += body.pop('world_tensor')+body['mass_kg']*((d @ d)*np.eye(3)-np.outer(d, d))
        self.report['inertials'] = {'total_mass_kg': total, 'zero_pose_world_com_m': center.tolist(),
            'zero_pose_total_inertia_at_com_kg_m2': combined.tolist(), 'bodies': bodies,
            'shape_free_fixed_zero_inertial_frames': zero_reference_frames}

    def expectations(self):
        for name, expected in self.expected.get('expected_joints', {}).items():
            info = self.joint_data.get(name)
            if info is None:
                self.error(f'Expected joint {name} absent')
                continue
            for key in ('parent', 'child', 'type'):
                if key in expected and info[key] != expected[key]:
                    self.error(f'{name}: unexpected {key}: {info[key]}')
            if info['type'] != 'fixed' and 'axis' in expected and not np.allclose(info['axis'], expected['axis'], atol=1e-8, rtol=0):
                self.error(f'{name}: unexpected joint axis')
            if 'xyz' in expected and not np.allclose(info['origin'][:3, 3], expected['xyz'], atol=1e-8, rtol=0):
                self.error(f'{name}: unexpected joint origin translation')
            if 'rpy' in expected and not np.allclose(info['origin'][:3, :3], rotation(expected['rpy']), atol=1e-8, rtol=0):
                self.error(f'{name}: unexpected joint origin rotation')
        joints = {}
        for name, info in self.joint_data.items():
            t = self.world[info['parent']] @ info['origin']
            joints[name] = {'parent': info['parent'], 'child': info['child'], 'type': info['type'],
                           'world_pivot_m': t[:3, 3].tolist(),
                           'world_axis': (t[:3, :3] @ info['axis']).tolist() if info['type'] != 'fixed' else None}
        self.report['zero_pose_joints'] = joints
        optical = {}
        for name in self.links:
            if 'optical' in name:
                r = self.world[name][:3, :3]
                optical[name] = {'local_x_in_root': r[:, 0].tolist(), 'local_y_in_root': r[:, 1].tolist(), 'local_z_in_root': r[:, 2].tolist()}
        self.report['optical_frames'] = optical
        for name in self.expected.get('ground_contacts', []):
            bound = self.report['zero_pose_world_bounds'].get(name, {}).get('collision')
            if not bound:
                self.error(f'Ground contact {name} has no collider')
            elif abs(bound['min'][2]) > .0001:
                self.error(f'Ground contact {name}: bottom z={bound["min"][2]:.6g} m, expected 0')
        contact_names = self.expected.get('ground_contacts', [])
        if len(contact_names) >= 3:
            points = np.array([self.world[name][:2, 3] for name in contact_names])
            centroid = points.mean(0)
            order = np.argsort(np.arctan2(points[:, 1]-centroid[1], points[:, 0]-centroid[0]))
            points = points[order]
            com = np.array(self.report['inertials']['zero_pose_world_com_m'])[:2]
            distances = []
            for a, b in zip(points, np.roll(points, -1, axis=0)):
                d = b-a
                distances.append(float((d[0]*(com-a)[1]-d[1]*(com-a)[0])/np.linalg.norm(d)))
            margin = min(distances)
            self.report['zero_pose_support_polygon'] = {'contact_centers_xy_m': points.tolist(),
                'com_xy_m': com.tolist(), 'minimum_margin_m': margin,
                'method': 'Static COM projection within polygon of contact centers, ignoring finite contact-patch size'}
            if margin < 0:
                self.warn(f'Zero-pose COM lies outside contact-center polygon by {-margin:.6g} m')

    def mirror_checks(self):
        pairs = self.expected.get('mirror_link_pairs')
        if pairs is None:
            pairs = [(name, 'right_'+name[5:]) for name in self.links
                     if name.startswith('left_') and 'right_'+name[5:] in self.links
                     and not any(word in name for word in ('finger', 'gripper', 'jaw'))]
        joint_pairs = [(name, 'right_'+name[5:]) for name, j in self.joint_data.items()
                       if name.startswith('left_') and 'right_'+name[5:] in self.joint_data
                       and j['type'] in ('revolute', 'prismatic') and j['mimic'] is None
                       and not any(word in name for word in ('finger', 'gripper', 'jaw'))]
        reflection = np.diag([1., -1., 1.])
        checks = []
        for fraction in (0., .17, -.13):
            positions = {}
            for left, right in joint_pairs:
                lo, hi = self.joint_data[left]['limits'] or (-1., 1.)
                value = np.clip(fraction*(hi-lo), lo, hi)
                positions[left] = positions[right] = float(value)
            world = self.fk(positions)
            errors = []
            for left, right in pairs:
                if left not in world or right not in world:
                    self.error(f'Mirror pair contains absent link: {left}, {right}')
                    continue
                deviation = float(np.linalg.norm(world[right][:3, 3]-reflection @ world[left][:3, 3]))
                orientation_deviation = (float(np.linalg.norm(world[right][:3, :3]-reflection @ world[left][:3, :3] @ reflection))
                                         if 'wheel' not in left else 0.)
                errors.append({'left': left, 'right': right, 'position_deviation_m': deviation,
                               'reflected_basis_deviation_frobenius': orientation_deviation})
                if deviation > 1e-7:
                    self.error(f'{left}/{right}: mirrored equal-command FK differs by {deviation:.6g} m')
                if orientation_deviation > 1e-7:
                    self.error(f'{left}/{right}: mirrored equal-command orientation basis differs by {orientation_deviation:.6g}')
            checks.append({'command_fraction_of_range': fraction, 'commands': positions, 'link_errors': errors})
        self.report['paired_mirror_fk'] = {'reflection_plane': 'root XZ plane (Y sign changes)',
            'method': 'Matched left/right joints receive equal nonzero scalar commands; origins and conjugate reflected basis matrices must match',
            'checks': checks}

    def sketch_dimensions(self):
        """Check independently transcribed R08 nominal geometry, not hardware accuracy."""
        path = self.package/'config'/'geometry_manifest.json'
        if not path.is_file():
            self.error('R08 source geometry manifest is missing')
            return
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        expected = {'base_length': .558, 'base_width': .404, 'base_height': .205,
                    'frame_width': .200, 'frame_depth': .200,
                    'post_size': .020, 'post_length': .500, 'post_bottom': .205,
                    'frame_center_x': -.070, 'ring_bottoms': [.205, .480, .555, .685],
                    'width_rail_length': .160, 'depth_rail_length': .160,
                    'shelf_thickness': .003, 'arm_root_z': .545, 'arm_root_y': .108,
                    'camera_center': [-.005, 0, .635],
                    'camera_optical_offset': [.034, .06925, .0065],
                    'camera_aperture_half_width': .078,
                    'camera_aperture_bottom': .603, 'camera_aperture_top': .6625,
                    'kinect_mass': .970}
        def same(actual_value, expected_value, tolerance=1e-9):
            try:
                a, b = np.asarray(actual_value, dtype=float), np.asarray(expected_value, dtype=float)
                return a.shape == b.shape and np.isfinite(a).all() and np.allclose(a, b, atol=tolerance, rtol=0)
            except (ValueError, TypeError):
                return False
        def require(actual_value, expected_value, label, tolerance=1e-9):
            if not same(actual_value, expected_value, tolerance):
                self.error(f'R08 {label}: expected {expected_value}, found {actual_value}')
        def dark_opaque(part):
            rgba = np.asarray(part.get('rgba', []), dtype=float)
            return rgba.shape == (4,) and np.isfinite(rgba).all() and np.max(rgba[:3]) <= .12 and abs(rgba[3]-1) < 1e-8

        actual = data.get('parameters', {})
        for key, value in expected.items():
            require(actual.get(key), value, f'dimension {key}')
        parts = data.get('links', {}).get('base_link', {}).get('parts', [])
        posts = [p for p in parts if p.get('name', '').startswith('post_')]
        rails = [p for p in parts if p.get('name', '').startswith('rail_')]
        if len(posts) != 4 or len(rails) != 16:
            self.error(f'R08 stock count: expected 4 posts / 16 rails; found {len(posts)} / {len(rails)}')
        post_centres = [(-.160, -.090, .455), (-.160, .090, .455),
                        (.020, -.090, .455), (.020, .090, .455)]
        unmatched = list(post_centres)
        for p in posts:
            require(p.get('size'), [.500], f'{p["name"]} upright stock length')
            if p.get('kind') != 'extrusion':
                self.error(f'R08 {p["name"]}: upright must be extrusion source geometry')
            match = next((q for q in unmatched if same(p.get('xyz'), q)), None)
            if match is None:
                self.error(f'R08 {p["name"]}: unexpected or duplicate post centre {p.get("xyz")}')
            else:
                unmatched.remove(match)
            require(np.abs(rotation(p.get('rpy', [0, 0, 0]))[:, 2]), [0, 0, 1], f'{p["name"]} upright direction')
            if not dark_opaque(p):
                self.error(f'R08 {p["name"]}: frame finish must be opaque black')
        rail_slots = []
        for z in (.215, .490, .565, .695):
            rail_slots.extend([(.160, [-.070, -.090, z], [1, 0, 0]),
                               (.160, [-.070, .090, z], [1, 0, 0]),
                               (.160, [-.160, 0, z], [0, 1, 0]),
                               (.160, [.020, 0, z], [0, 1, 0])])
        rail_counts = {'160_mm_width': 0, '160_mm_depth': 0}
        for p in rails:
            axis = np.abs(rotation(p.get('rpy', [0, 0, 0]))[:, 2])
            match = next((q for q in rail_slots if same(p.get('size'), [q[0]]) and same(p.get('xyz'), q[1]) and same(axis, q[2])), None)
            if match is None:
                self.error(f'R08 {p["name"]}: rail length, centre, direction or ring placement differs from the 200x200 frame')
            else:
                rail_slots.remove(match)
                rail_counts['160_mm_width' if same(match[2], [0, 1, 0]) else '160_mm_depth'] += 1
            if p.get('kind') != 'extrusion' or not dark_opaque(p):
                self.error(f'R08 {p["name"]}: horizontal stock must be black extrusion source geometry')
        require(list(rail_counts.values()), [8, 8], 'width/depth rail counts')

        floors = [p for p in parts if p.get('name', '').startswith('polycarbonate_floor_')]
        if len(floors) != 4:
            self.error(f'R08 shelves: expected four notched floor/roof source parts, found {len(floors)}')
        base_colliders = self.geometries.get('base_link', {}).get('collision', [])
        post_shapes = [g for g in base_colliders if g['name'].startswith(('post_', 'base_link_post_'))]
        remaining_posts = list(post_centres)
        if len(post_shapes) != 4:
            self.error(f'R08 frame: expected four post box colliders, found {len(post_shapes)}')
        for g in post_shapes:
            require(g['hi']-g['lo'], [.020, .020, .500], f'{g["name"]} post collider dimensions')
            require(g['origin'][:3, :3], np.eye(3), f'{g["name"]} post collider orientation')
            match = next((q for q in remaining_posts if same(g['origin'][:3, 3], q)), None)
            if g['type'] != 'box' or match is None:
                self.error(f'R08 {g["name"]}: unexpected or duplicated URDF post collider')
            else:
                remaining_posts.remove(match)
        rail_shapes = [g for g in base_colliders if g['name'].startswith(('rail_', 'base_link_rail_'))]
        remaining_rails = []
        for z in (.215, .490, .565, .695):
            remaining_rails.extend([([.160, .020, .020], [-.070, -.090, z]),
                                    ([.160, .020, .020], [-.070, .090, z]),
                                    ([.020, .160, .020], [-.160, 0, z]),
                                    ([.020, .160, .020], [.020, 0, z])])
        if len(rail_shapes) != 16:
            self.error(f'R08 frame: expected sixteen rail box colliders, found {len(rail_shapes)}')
        for g in rail_shapes:
            match = next((q for q in remaining_rails if same(g['hi']-g['lo'], q[0]) and same(g['origin'][:3, 3], q[1]) and same(g['origin'][:3, :3], np.eye(3))), None)
            if g['type'] != 'box' or match is None:
                self.error(f'R08 {g["name"]}: URDF rail collider differs from the independently specified frame')
            else:
                remaining_rails.remove(match)
        floor_area = .200*.200-4*.020*.020
        for i, z in enumerate((.205, .480, .555, .685)):
            named = [p for p in floors if p.get('name') == f'polycarbonate_floor_{i}']
            if len(named) != 1:
                self.error(f'R08 missing uniquely identified notched floor {i}')
                continue
            p = named[0]
            if p.get('kind') != 'prism':
                self.error(f'R08 {p["name"]}: expected notched prism, not a full rectangular sheet crossing the posts')
            require(p.get('size'), [.200, .200, .003], f'{p["name"]} outside reservation and thickness')
            require(p.get('xyz'), [-.070, 0, z+.0215], f'{p["name"]} rail-top placement')
            expected_polygon = np.array([[-.100, -.080], [-.080, -.080], [-.080, -.100], [.080, -.100],
                                         [.080, -.080], [.100, -.080], [.100, .080], [.080, .080],
                                         [.080, .100], [-.080, .100], [-.080, .080], [-.100, .080]])
            polygon = np.asarray(p.get('polygon', []), dtype=float)
            if polygon.shape != (12, 2) or not any(same(polygon, np.roll(q, k, axis=0)) for q in (expected_polygon, expected_polygon[::-1]) for k in range(12)):
                self.error(f'R08 {p["name"]}: source polygon differs from the 200mm square with 20mm corner notches')
            else:
                area = abs(float(np.sum(polygon[:, 0]*np.roll(polygon[:, 1], -1)-polygon[:, 1]*np.roll(polygon[:, 0], -1)))/2)
                require(area, floor_area, f'{p["name"]} independently calculated polygon area')
            density = actual.get('polycarbonate_density')
            if isinstance(density, (int, float)) and math.isfinite(density) and density > 0:
                require(p.get('mass'), floor_area*.003*density, f'{p["name"]} mass from notched area and declared density')
            floor_geos = [g for g in base_colliders if g['name'].startswith((f'floor_{i}_', f'base_link_floor_{i}_'))]
            if len(floor_geos) != 3 or any(g['type'] != 'box' for g in floor_geos):
                self.error(f'R08 floor {i}: expected three box colliders for the notched shelf decomposition')
            expected_sections = [([.160, .200, .003], [-.070, 0, z+.0215]),
                                 ([.020, .160, .003], [-.160, 0, z+.0215]),
                                 ([.020, .160, .003], [.020, 0, z+.0215])]
            for g in floor_geos:
                t = self.world['base_link'] @ g['origin']
                size = g['hi']-g['lo']
                centre = transform_points(t, ((g['lo']+g['hi'])/2)[None])[0]
                match = next((q for q in expected_sections if same(size, q[0]) and same(centre, q[1]) and same(t[:3, :3], np.eye(3))), None)
                if match is None:
                    self.error(f'R08 {g["name"]}: unexpected notched floor collision section')
                else:
                    expected_sections.remove(match)
                half = size/2
                bounds = transform_points(t, box_vertices(g['lo'], g['hi']))
                lo, hi = bounds.min(0), bounds.max(0)
                for q in post_centres:
                    if oriented_box_intersects((centre, t[:3, :3], half), (np.asarray(q), np.eye(3), np.array([.010, .010, .250]))):
                        self.error(f'R08 {g["name"]}: notched shelf collider penetrates a corner post')
                supported = False
                for rail in rails:
                    rt = rotation(rail.get('rpy', [0, 0, 0]))
                    rh = np.array([.010, .010, float(rail['size'][0])/2])
                    extent = np.abs(rt) @ rh
                    rlo, rhi = np.asarray(rail['xyz'])-extent, np.asarray(rail['xyz'])+extent
                    overlap = np.minimum(hi[:2], rhi[:2])-np.maximum(lo[:2], rlo[:2])
                    if abs(lo[2]-rhi[2]) < 1e-9 and np.all(overlap > 1e-6):
                        supported = True
                        break
                if not supported:
                    self.error(f'R08 {g["name"]}: shelf section has no nominal rail-top support')

        battery_parts = [p for p in parts if p.get('name') == 'noco_gb70']
        if len(battery_parts) != 1:
            self.error('R08 expected one upright NOCO GB70 source body')
        for p in battery_parts:
            require(p.get('size'), [.069, .099, .222], 'upright GB70 body depth/width/height')
            require(p.get('xyz'), [-.070, 0, .343], 'upright GB70 body centre')
            require(rotation(p.get('rpy', [0, 0, 0])), np.eye(3), 'upright GB70 box orientation')
        reservations = [g for g in base_colliders if g['name'] in ('noco_installed_reserve', 'base_link_noco_installed_reserve')]
        if len(reservations) != 1:
            self.error('R08 expected one upright GB70 full installation reservation')
        for g in reservations:
            require(g['hi']-g['lo'], [.070, .152, .222], 'upright GB70 installed reservation dimensions')
            t = self.world['base_link'] @ g['origin']
            require(t[:3, :3], np.eye(3), 'upright GB70 installed reservation orientation')
            points = transform_points(t, box_vertices(g['lo'], g['hi']))
            lo, hi = points.min(0), points.max(0)
            require((lo+hi)/2, [-.070, 0, .343], 'upright GB70 installed reservation centre')
            require(lo[2], .232, 'GB70 installed reservation support datum')
            if lo[0] < -.150-1e-9 or hi[0] > .010+1e-9 or lo[1] < -.080-1e-9 or hi[1] > .080+1e-9 or hi[2] > .480+1e-9:
                self.error('R08 GB70 installation reservation exceeds the clear lower bay')
            require([lo[1]+.080, .080-hi[1]], [.004, .004], 'upright GB70 installed lateral clearance')

        sides = [p for p in parts if p.get('name', '').startswith(('side_-1_', 'side_1_', 'side_left_', 'side_right_')) and p.get('kind') == 'box']
        fronts = [p for p in parts if any(tag in p.get('name', '') for tag in ('front_sheet', 'front_door')) and p.get('kind') == 'box']
        if not sides or not fronts:
            self.error('R08 source register must identify side panels and front sheet/door components')
        for p in sides+fronts:
            if not dark_opaque(p):
                self.error(f'R08 {p["name"]}: front and side panels must have an opaque matte-black appearance')
        for p in sides:
            if p.get('name', '').endswith(('_lower', '_upper')):
                require(p.get('size', [None])[0], .200, f'{p["name"]} outside-frame side-panel depth')
            require(abs(p.get('xyz', [None, None])[1]), .101, f'{p["name"]} outside-frame side-panel plane')
            require(p.get('size', [None, None])[1], .002, f'{p["name"]} side-panel thickness')
            extent = np.abs(rotation(p.get('rpy', [0, 0, 0]))) @ (np.asarray(p['size'], dtype=float)/2)
            lo, hi = np.asarray(p['xyz'])-extent, np.asarray(p['xyz'])+extent
            if lo[0] < -.170-1e-9 or hi[0] > .030+1e-9 or lo[1] < -.102-1e-9 or hi[1] > .102+1e-9:
                self.error(f'R08 {p["name"]}: side sheet exceeds the 204mm covered-body or 200mm frame-depth envelope')
        aperture = (np.array([.031, 0, .63275]), np.eye(3), np.array([.001, .078, .02975]))
        for p in fronts:
            require(p.get('size', [None])[0], .002, f'{p["name"]} front-door sheet thickness')
            require(p.get('xyz', [None])[0], .031, f'{p["name"]} outside-frame front-door plane')
            if p.get('name', '').endswith(('_lower', '_upper')):
                require(p.get('size', [None, None])[1], .200, f'{p["name"]} full front-door width')
            shape = (np.asarray(p['xyz'], dtype=float), rotation(p.get('rpy', [0, 0, 0])), np.asarray(p['size'], dtype=float)/2)
            if oriented_box_intersects(shape, aperture):
                self.error(f'R08 {p["name"]}: opaque sheet obstructs the 156x59.5mm optical aperture')
        rear = [p for p in parts if p.get('name') == 'rear_door_closed']
        if len(rear) != 1:
            self.error('R08 expected one clear rear service door')
        for p in rear:
            require(p.get('size', [None])[0], .002, 'rear-door thickness')
            require(p.get('size', [None, None])[1], .200, 'full rear-door width')
            require(p.get('xyz', [None])[0], -.171, 'outside-frame rear-door plane')
        # Fixed parts share base_link, so inter-link screening cannot discover
        # a cover crossing a shelf. Check these interfaces explicitly.
        fixed_shelves = [g for g in base_colliders if g['name'].startswith(('floor_', 'base_link_floor_'))]
        source_camera_shelves = [p for p in parts if p.get('name') == 'camera_shelf' and p.get('kind') == 'box']
        for p in fronts+sides+rear:
            cover = (np.asarray(p['xyz'], dtype=float), rotation(p.get('rpy', [0, 0, 0])), np.asarray(p['size'], dtype=float)/2)
            for g in fixed_shelves:
                t = self.world['base_link'] @ g['origin']
                centre = transform_points(t, ((g['lo']+g['hi'])/2)[None])[0]
                shelf = (centre, t[:3, :3], (g['hi']-g['lo'])/2)
                if oriented_box_intersects(cover, shelf):
                    self.error(f'R08 fixed construction: {p["name"]} penetrates {g["name"]}')
            for shelf in source_camera_shelves:
                shape = (np.asarray(shelf['xyz'], dtype=float), rotation(shelf.get('rpy', [0, 0, 0])), np.asarray(shelf['size'], dtype=float)/2)
                if oriented_box_intersects(cover, shape):
                    self.error(f'R08 fixed construction: {p["name"]} penetrates {shelf["name"]}')
        if any('t12' in p.get('name', '').lower() or 'xiaomi' in p.get('name', '').lower() for p in parts):
            self.error('R08 base source still includes obsolete Xiaomi/T12 components')

        structure = self.report.get('structure', {})
        require(structure.get('link_count'), 23, 'link count')
        require(structure.get('joint_count'), 22, 'joint count')
        if structure.get('joint_types') != {'fixed': 4, 'continuous': 4, 'revolute': 14}:
            self.error(f'R08 joint types differ: {structure.get("joint_types")}')
        require(structure.get('independent_joint_coordinates'), 16, 'independent coordinate count')
        require(data.get('independent_commands'), 14, 'commanded coordinate count in source register')

        def child_joint(child, parent, kind, xyz, axis):
            candidates = [(n, j) for n, j in self.joint_data.items() if j['child'] == child]
            if len(candidates) != 1:
                self.error(f'R08 {child}: expected one parent joint')
                return None
            name, j = candidates[0]
            if j['parent'] != parent or j['type'] != kind:
                self.error(f'R08 {name}: expected {kind} joint from {parent}')
            require(j['origin'][:3, 3], xyz, f'{name} parent-frame pivot')
            require(j['origin'][:3, :3], np.eye(3), f'{name} parent-frame rotation')
            require(j['axis'], axis, f'{name} local axis')
            return name
        for side, sign in (('left', 1), ('right', -1)):
            child_joint(side+'_wheel', 'base_link', 'continuous', [-.180, sign*.177, .0925], [0, 1, 0])
            require(self.world.get(side+'_wheel', np.eye(4))[:3, 3], [-.180, sign*.177, .0925], f'{side} wheel world centre')
            shapes = self.geometries.get(side+'_wheel', {}).get('collision', [])
            rollers = [g for g in shapes if g['type'] == 'cylinder' and same(g['hi']-g['lo'], [.185, .185, .050])]
            if len(rollers) != 1:
                self.error(f'R08 {side} wheel: expected one 92.5mm-radius, 50mm-wide cylinder contact')
            for g in rollers:
                require(g['origin'][:3, 3], [0, 0, 0], f'{side} wheel collider centre')
                require(np.abs(g['origin'][:3, :3][:, 2]), [0, 1, 0], f'{side} rolling cylinder axis')
        swivel = child_joint('caster_swivel_link', 'base_link', 'continuous', [.215, 0, .110], [0, 0, 1])
        roller = child_joint('caster_link', 'caster_swivel_link', 'continuous', [-.020, 0, -.070], [0, 1, 0])
        require(self.world.get('caster_link', np.eye(4))[:3, 3], [.195, 0, .040], 'neutral caster wheel centre')
        caster_shapes = self.geometries.get('caster_link', {}).get('collision', [])
        caster_rollers = [g for g in caster_shapes if g['type'] == 'cylinder' and same(g['hi']-g['lo'], [.080, .080, .040])]
        if len(caster_rollers) != 1:
            self.error('R08 caster: expected one 40mm-radius, 40mm-wide rolling cylinder')
        for g in caster_rollers:
            require(g['origin'][:3, 3], [0, 0, 0], 'caster wheel collider centre')
            require(np.abs(g['origin'][:3, :3][:, 2]), [0, 1, 0], 'caster rolling cylinder axis')
        if any(frozenset(pair) == frozenset(('base_link', 'caster_link')) for pair in self.expected.get('allow_collision_pairs', [])):
            self.error('R08 caster wheel/chassis collisions must not be suppressed by a broad allowed pair')
        contacts = self.expected.get('ground_contacts', [])
        if set(contacts) != {'left_wheel', 'right_wheel', 'caster_link'} or len(contacts) != 3:
            self.error(f'R08 expected three rolling ground-contact links, found {contacts}')
        passive_names = [name for name in (swivel, roller) if name is not None]
        commanded = [n for n, j in self.joint_data.items() if j['type'] != 'fixed' and j['mimic'] is None and n not in passive_names]
        require(len(commanded), 14, 'independent actuated coordinates after excluding the two passive caster joints')

        camera = self.geometries.get('camera_mount', {}).get('collision', [])
        camera_bodies = [g for g in camera if g['type'] == 'box' and same(g['hi']-g['lo'], [.070, .156, .056])]
        if len(camera_bodies) != 1:
            self.error('R08 camera: expected provisional casing-free 70x156x56mm module reservation')
        for g in camera_bodies:
            t = self.world['camera_mount'] @ g['origin']
            centre = transform_points(t, ((g['lo']+g['hi'])/2)[None])[0]
            require(centre, [-.006, 0, .6315], 'provisional bare-camera world reservation centre')
            require(t[:3, :3], np.eye(3), 'straight-ahead bare-camera reservation rotation')
            points = transform_points(t, box_vertices(g['lo'], g['hi']))
            lo, hi = points.min(0), points.max(0)
            require(lo, [-.041, -.078, .6035], 'bare-camera reservation lower bounds')
            require(hi, [.029, .078, .6595], 'bare-camera reservation upper bounds')
            if lo[0] < -.170-1e-9 or hi[0] > .030+1e-9 or lo[1] < -.080-1e-9 or hi[1] > .080+1e-9:
                self.error('R08 provisional camera reservation exceeds the frame or between-post lateral opening')
            require([lo[1]+.080, .080-hi[1]], [.002, .002], 'bare-camera reservation lateral clearances')
            require(.030-hi[0], .001, 'bare-camera front frame setback')
        camera_joint = self.joint_data.get('camera_mount_joint')
        if camera_joint is not None:
            require(camera_joint['origin'][:3, 3], [-.005, 0, .635], 'bare-camera mount origin')
        optical_joint = self.joint_data.get('camera_optical_joint')
        if optical_joint is not None:
            require(optical_joint['origin'][:3, 3], [.034, .06925, .0065], 'provisional depth optical-frame offset')
        camera_parts = data.get('links', {}).get('camera_mount', {}).get('parts', [])
        if any('housing' in p.get('name', '').lower() or 'case' in p.get('name', '').lower() for p in camera_parts):
            self.error('R08 camera visual source still declares a casing/housing component')
        module_parts = {
            'kinect_logic_board_provisional': ([.045, .150, .003], [-.005, 0, -.022]),
            'kinect_heatspreader_provisional': ([.045, .100, .020], [-.005, 0, -.0105]),
            'kinect_optical_carrier_provisional': ([.024, .154, .025], [.018, 0, .012])}
        for name, (size, xyz) in module_parts.items():
            found = [p for p in camera_parts if p.get('name') == name]
            if len(found) != 1:
                self.error(f'R08 expected one provisional bare-camera component {name}')
            for p in found:
                require(p.get('size'), size, f'{name} provisional dimensions')
                require(p.get('xyz'), xyz, f'{name} provisional local centre')
        lens_parts = {p.get('name'): p for p in camera_parts if p.get('name') in ('rgb_lens', 'depth_lens')}
        if set(lens_parts) != {'rgb_lens', 'depth_lens'}:
            self.error('R08 expected provisional RGB and depth optical parts')
        else:
            require(lens_parts['rgb_lens'].get('xyz', [0, None])[1], -.06925, 'provisional RGB lateral position')
            require(lens_parts['depth_lens'].get('xyz', [0, None])[1], .06925, 'provisional depth lateral position')
            require(lens_parts['depth_lens']['xyz'][1]-lens_parts['rgb_lens']['xyz'][1], .1385, 'uncalibrated nominal RGB-depth spacing')
        require(sum(float(p.get('mass', 0)) for p in camera_parts), .970, 'retained conservative camera mass budget')
        for side, sign in (('left', 1), ('right', -1)):
            name = side+'_arm_base_joint'
            j = self.joint_data.get(name)
            if j is None:
                self.error(f'R08 missing {name}')
            else:
                require((self.world[j['parent']] @ j['origin'])[:3, 3], [-.070, sign*.108, .545], f'{name} world root pivot')

        self.report['r08_dimension_register_check'] = {
            'source': 'Independently transcribed R08 construction constants and explicit provisional simulation geometry; checked against source register and URDF transforms/colliders',
            'expected_parameters_m': expected, 'post_count': len(posts), 'rail_counts': rail_counts,
            'frame_clear_width_depth_m': [.160, .160], 'provisional_bare_camera_side_clearance_m': .002,
            'frame_outside_width_depth_m': [.200, .200], 'covered_body_width_depth_m': [.204, .204],
            'front_door_aperture_width_height_m': [.156, .0595], 'bare_camera_front_frame_setback_m': .001,
            'provisional_bare_camera_reservation_depth_width_height_m': [.070, .156, .056],
            'upright_GB70_body_depth_width_height_m': [.069, .099, .222],
            'upright_GB70_installation_depth_width_height_m': [.070, .152, .222],
            'nominal_uncalibrated_RGB_depth_spacing_m': .1385,
            'notched_floor_outside_size_m': [.200, .200, .003], 'notched_floor_area_m2': floor_area,
            'independent_coordinates': 16, 'commanded_coordinates': 14, 'passive_caster_joints': passive_names,
            'source_categories': {
                'manufacturer_envelope': 'WR141E exterior 558x404x205mm only; not a measured body surface',
                'supplied_stock': 'Four 20x20x500mm posts; sixteen 200mm rails cut to 160mm',
                'approved_construction_change': '200x200mm frame and floors, 204x204mm externally covered body, 160x160mm clear opening, black frame/front/sides, internal casing-free camera reservation',
                'provisional_unmeasured_simulation_inputs': 'Bare-camera module fit, PCB/optics/heat-sink sizes, camera optical calibration, retained 970g camera mass budget, wheel/caster geometry, chassis/frame mounting datum, arm pivots and all mass/actuator values'},
            'limitations': 'Confirms internal consistency with nominal R08 construction and declared provisional inputs. Does not verify physical hardware, as-built tolerances, payload, mounting strength or real-world dynamics.'}

    def gravity_loads(self, positions):
        world = self.fk(positions)
        body = {}
        for name, link in self.links.items():
            node = link.find('inertial')
            if node is not None:
                mass = float(node.find('mass').get('value'))
                if mass > 0:
                    body[name] = (mass, (world[name] @ origin(node.find('origin')))[:3, 3])
        def descendants(link):
            result = [link]
            for child, _ in self.children[link]:
                result.extend(descendants(child))
            return result
        result = {}
        for name, info in self.joint_data.items():
            if info['type'] not in ('revolute', 'continuous', 'prismatic'):
                continue
            t = world[info['parent']] @ info['origin']
            axis, pivot = t[:3, :3] @ info['axis'], t[:3, 3]
            load = 0.
            for child in descendants(info['child']):
                if child not in body:
                    continue
                mass, center = body[child]
                force = np.array([0., 0., -9.80665*mass])
                load += float(axis @ (force if info['type'] == 'prismatic' else np.cross(center-pivot, force)))
            limit = float(self.joints[name].find('limit').get('effort'))
            result[name] = {'gravity_effort': load, 'absolute_gravity_effort': abs(load),
                            'declared_effort_limit': limit, 'fraction_of_declared_limit': abs(load)/limit,
                            'unit': 'N' if info['type'] == 'prismatic' else 'N m'}
        return result

    def collisions(self, positions):
        world = self.fk(positions)
        shapes = []
        for link, geos in self.geometries.items():
            for g in geos['collision']:
                t = world[link] @ g['origin']
                center = (g['lo']+g['hi'])/2
                half = (g['hi']-g['lo'])/2
                obb = (transform_points(t, center[None])[0], t[:3, :3], half)
                shapes.append((link, g, obb))
        allowed = {frozenset(pair) for pair in self.expected.get('allow_collision_pairs', [])}
        candidates = {}
        for i, (a, ga, ba) in enumerate(shapes):
            for b, gb, bb in shapes[i+1:]:
                pair = frozenset((a, b))
                if a == b or pair in allowed:
                    continue
                if (a in self.parents and self.parents[a][0] == b) or (b in self.parents and self.parents[b][0] == a):
                    continue
                if oriented_box_intersects(ba, bb):
                    key = tuple(sorted((a, b)))
                    entry = candidates.setdefault(key, {'links': list(key), 'exact_box_pairs': 0, 'conservative_bound_pairs': 0})
                    field = 'exact_box_pairs' if ga['exact_box'] and gb['exact_box'] else 'conservative_bound_pairs'
                    entry[field] += 1
        return list(candidates.values())

    def sweep(self):
        zero = self.collisions({})
        zero_pairs = {tuple(c['links']) for c in zero}
        sweeps = []
        gravity = self.gravity_loads({})
        maxima = {name: dict(value, pose='zero pose') for name, value in gravity.items()}
        requested = self.expected.get('sweep_joint_names')
        if requested is None:
            requested = [name for name, j in self.joint_data.items()
                         if j['type'] in ('revolute', 'prismatic') and j['mimic'] is None]
        else:
            requested = list(requested)
        caster_swivels = [name for name, j in self.joint_data.items()
                         if j['child'] == 'caster_swivel_link' and j['type'] == 'continuous']
        requested.extend(name for name in caster_swivels if name not in requested)
        for name in requested:
            j = self.joint_data.get(name)
            is_caster_swivel = name in caster_swivels
            if not j or (j['limits'] is None and not is_caster_swivel):
                self.warn(f'Cannot sweep {name}: missing bounded joint')
                continue
            limits = (-math.pi, math.pi) if is_caster_swivel else j['limits']
            sample_count = max(17, self.samples) if is_caster_swivel else self.samples
            candidates = {}
            for q in np.linspace(*limits, sample_count):
                for target, value in self.gravity_loads({name: float(q)}).items():
                    if value['absolute_gravity_effort'] > maxima[target]['absolute_gravity_effort']:
                        maxima[target] = dict(value, pose=f'{name}={q:.8g}')
                for item in self.collisions({name: float(q)}):
                    key = tuple(item['links'])
                    if key not in zero_pairs:
                        value = candidates.setdefault(key, {'links': list(key), 'first_sample': float(q), 'last_sample': float(q), 'sample_count': 0})
                        value['last_sample'] = float(q)
                        value['sample_count'] += 1
            sweeps.append({'joint': name, 'samples': sample_count, 'limits': list(limits),
                           'range_kind': 'one full continuous swivel revolution' if is_caster_swivel else 'declared bounded range',
                           'additional_candidates': list(candidates.values())})
        count = len(zero)+sum(len(s['additional_candidates']) for s in sweeps)
        if count:
            self.warn(f'{count} collision-screening candidate groups require inspection; see collision_screening')
        self.report['collision_screening'] = {'method': 'Oriented bounding box SAT; adjacent links and explicit allowed pairs excluded',
             'zero_pose_candidates': zero, 'one_joint_sweeps': sweeps,
             'excluded_pairs': self.expected.get('allow_collision_pairs', [])}
        self.report['estimated_static_gravity_loads'] = {'gravity_m_s2': 9.80665, 'zero_pose': gravity,
            'maximum_in_checked_poses': maxima,
            'limitations': 'Based on declared estimated masses; ignores payload, acceleration, friction, gear efficiency and multi-joint combinations.'}
        for name, value in maxima.items():
            if value['fraction_of_declared_limit'] > 1:
                self.warn(f'{name}: estimated static gravity effort {value["absolute_gravity_effort"]:.5g} {value["unit"]} exceeds declared limit {value["declared_effort_limit"]:.5g} at {value["pose"]}')

    def run(self):
        try:
            self.parse()
            if not self.errors:
                self.inspect_geometry()
                self.inspect_inertias()
                self.expectations()
                self.sketch_dimensions()
                self.mirror_checks()
                self.sweep()
        except Exception as e:
            self.error(f'Validation failed: {type(e).__name__}: {e}')
        self.report['errors'] = self.errors
        self.report['warnings'] = self.warnings
        self.report['status'] = 'PASS_WITH_REVIEW_NOTES' if not self.errors and self.warnings else ('PASS' if not self.errors else 'FAIL')
        return self.report


def markdown(report):
    lines = ['# Underbot independent authoring validation', '', f"Status: **{report['status']}**", '',
        report['scope']+'.', '', f"Input: `{Path(report['file']).name}`", '']
    if 'structure' in report:
        s = report['structure']
        lines += [f"Tree: {s['link_count']} links, {s['joint_count']} joints, root `{s['root']}`, {s['independent_joint_coordinates']} independent coordinates.", '']
    if 'inertials' in report:
        v = report['inertials']
        lines += [f"Estimated total mass: {v['total_mass_kg']:.6f} kg. Zero-pose centre of mass in root frame: {v['zero_pose_world_com_m']} m.",
                  'Each massive-link inertia was checked for finite positive mass, positive principal moments and the principal-moment triangle inequalities. Shape-free fixed reference frames may explicitly declare zero mass and a zero tensor; these contribute no mass and may have no moving descendants.', '']
    if 'r08_dimension_register_check' in report:
        lines += ['R08 nominal construction was checked independently: WR141E 558 × 404 × 205 mm published envelope; 200 ×200 mm frame and floors; 204 ×204 mm covered body with external 2 mm sheets; four 500 mm posts; sixteen 160 mm rails; 160 ×160 mm clear opening; black frame/front/sides; upright GB70 body and installation reservation; casing-free camera reservation with 2 mm lateral gaps; wheel contacts, two passive caster joints and arm root datums. The stripped camera module dimensions, optics, retained camera mass, wheel/caster geometry and mounting positions are provisional simulation inputs. These checks establish consistency and fit of declared reservations, not verified hardware fit. Fixed cover/shelf interfaces are checked for penetration independently of inter-link screening. The source register, URDF transforms/colliders and all referenced meshes were checked separately.', '']
    for title, values in [('Errors', report['errors']), ('Review notes', report['warnings']), ('Scope limits', report['limitations'])]:
        lines += [f'## {title}', '']
        lines += [f'- {v}' for v in values] if values else ['None.']
        lines += ['']
    collision = report.get('collision_screening', {})
    lines += ['## Collision screening', '', collision.get('method', 'Not performed')+'.', '']
    for c in collision.get('zero_pose_candidates', []):
        lines += [f"- Zero pose: `{c['links'][0]}` / `{c['links'][1]}`; {c['exact_box_pairs']} box intersections, {c['conservative_bound_pairs']} conservative candidates."]
    for sweep in collision.get('one_joint_sweeps', []):
        if sweep['additional_candidates']:
            lines += [f"- `{sweep['joint']}`: {len(sweep['additional_candidates'])} additional pair groups over {sweep['samples']} samples; detailed angles in JSON."]
    if not collision.get('zero_pose_candidates') and not any(s.get('additional_candidates') for s in collision.get('one_joint_sweeps', [])):
        lines += ['No nonadjacent candidates in the checked poses. This does not prove complete collision freedom.']
    lines += ['', 'The JSON report includes link world bounds, pivot/axis directions, optical-frame basis vectors, STL topology, COM and inertia results.', '']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('urdf', nargs='?', default=str(Path(__file__).resolve().parents[1]/'urdf'/'underbot.urdf'))
    ap.add_argument('--expectations', type=Path)
    ap.add_argument('--report', type=Path, help='JSON report path; a Markdown sibling is also written')
    ap.add_argument('--samples', type=int, default=9, help='Samples per one-joint sweep (minimum 3)')
    args = ap.parse_args()
    path = Path(args.urdf).resolve()
    epath = args.expectations or path.parent.parent/'config'/'validation_expectations.json'
    expectations = json.loads(epath.read_text(encoding='utf-8-sig')) if epath.is_file() else {}
    report = Validator(path, expectations, max(3, args.samples)).run()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        args.report.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'errors': report['errors'], 'warnings': report['warnings'],
                      'links': report.get('structure', {}).get('link_count'),
                      'joints': report.get('structure', {}).get('joint_count'),
                      'mass_kg': report.get('inertials', {}).get('total_mass_kg')}, indent=2))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
