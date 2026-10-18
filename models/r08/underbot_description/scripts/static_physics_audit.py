#!/usr/bin/env python3
"""Independent URDF-only, level-ground, no-payload static physics audit.

Requires Python and NumPy. This does not import the model generator, manifest,
parameter register, simulation engines, or authoring validator. Inertial masses
and COM origins, kinematic transforms, efforts and contact radii come from URDF.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

GRAVITY = 9.80665


def vec(value, default=(0., 0., 0.)):
    return np.asarray([float(x) for x in value.split()] if value else default)


def rpy_matrix(v):
    r, p, y = v
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                     [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
                     [-sp, cp*sr, cp*cr]])


def origin(element):
    t = np.eye(4)
    if element is not None:
        t[:3, :3] = rpy_matrix(vec(element.get('rpy')))
        t[:3, 3] = vec(element.get('xyz'))
    return t


def axis_matrix(axis, q):
    x, y, z = axis
    k = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    return np.eye(3) + math.sin(q)*k + (1.-math.cos(q))*(k @ k)


class Model:
    def __init__(self, path):
        self.path = path
        self.raw = path.read_bytes()
        root = ET.fromstring(self.raw)
        self.links = {}
        for e in root.findall('link'):
            inertial = e.find('inertial')
            if inertial is None:
                mass, com, tensor = 0., np.zeros(3), None
            else:
                mass = float(inertial.find('mass').get('value'))
                com = origin(inertial.find('origin'))[:3, 3]
                v = inertial.find('inertia').attrib
                tensor = np.array([[float(v['ixx']), float(v['ixy']), float(v['ixz'])],
                                   [float(v['ixy']), float(v['iyy']), float(v['iyz'])],
                                   [float(v['ixz']), float(v['iyz']), float(v['izz'])]])
                if (mass < 0. or not np.isfinite(tensor).all()
                        or (mass > 0. and np.linalg.eigvalsh(tensor).min() <= 0.)
                        or (mass == 0. and not np.allclose(tensor, 0., atol=1e-15))):
                    raise ValueError(f'Invalid positive-mass inertial: {e.get("name")}')
            self.links[e.get('name')] = {'mass': mass, 'com': com, 'tensor': tensor, 'xml': e}
        self.joints = {}
        for e in root.findall('joint'):
            limit, mimic = e.find('limit'), e.find('mimic')
            axis = vec(e.find('axis').get('xyz')) if e.find('axis') is not None else np.array([1., 0., 0.])
            axis = axis/np.linalg.norm(axis)
            self.joints[e.get('name')] = {
                'parent': e.find('parent').get('link'), 'child': e.find('child').get('link'),
                'type': e.get('type'), 'origin': origin(e.find('origin')), 'axis': axis,
                'effort': float(limit.get('effort')) if limit is not None else None,
                'lower': float(limit.get('lower')) if limit is not None and limit.get('lower') is not None else None,
                'upper': float(limit.get('upper')) if limit is not None and limit.get('upper') is not None else None,
                'mimic': (mimic.get('joint'), float(mimic.get('multiplier', '1')), float(mimic.get('offset', '0'))) if mimic is not None else None}
        children = {j['child'] for j in self.joints.values()}
        roots = set(self.links)-children
        if len(roots) != 1:
            raise ValueError('Exactly one URDF root is required')
        self.root = roots.pop()
        self.order, pending, seen = [], dict(self.joints), {self.root}
        while pending:
            eligible = [n for n, j in pending.items() if j['parent'] in seen]
            if not eligible:
                raise ValueError('Disconnected/cyclic joint graph')
            for n in eligible:
                self.order.append(n)
                seen.add(pending.pop(n)['child'])
        self.desc = {}
        for name, j in self.joints.items():
            descendants = {j['child']}
            for n in self.order:
                if self.joints[n]['parent'] in descendants:
                    descendants.add(self.joints[n]['child'])
            self.desc[name] = descendants
        self.mass = sum(l['mass'] for l in self.links.values())
        self.arm_inputs = [n for n, j in self.joints.items() if j['type'] == 'revolute' and j['mimic'] is None]
        self.moving = [n for n, j in self.joints.items() if j['type'] in ('revolute', 'continuous')]

    def coordinate(self, name, q, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            raise ValueError('Cyclic mimic coordinates')
        seen.add(name)
        mimic = self.joints[name]['mimic']
        return self.coordinate(mimic[0], q, seen)*mimic[1]+mimic[2] if mimic else q.get(name, 0.)

    def input_dependency(self, name):
        factor = 1.
        seen = set()
        while self.joints[name]['mimic']:
            if name in seen:
                raise ValueError('Cyclic mimic coordinates')
            seen.add(name)
            name, multiplier, _ = self.joints[name]['mimic']
            factor *= multiplier
        return name, factor

    def evaluate(self, q):
        transforms, pivots, axes = {self.root: np.eye(4)}, {}, {}
        for name in self.order:
            j = self.joints[name]
            before = transforms[j['parent']] @ j['origin']
            pivots[name], axes[name] = before[:3, 3], before[:3, :3] @ j['axis']
            motion = np.eye(4)
            value = self.coordinate(name, q)
            if j['type'] in ('continuous', 'revolute'):
                motion[:3, :3] = axis_matrix(j['axis'], value)
            elif j['type'] == 'prismatic':
                motion[:3, 3] = j['axis']*value
            transforms[j['child']] = before @ motion
        coms = {n: transforms[n][:3, :3] @ l['com'] + transforms[n][:3, 3] for n, l in self.links.items()}
        weighted = sum((self.links[n]['mass']*c for n, c in coms.items()), np.zeros(3))
        holding, independent = {}, {}
        for name in self.moving:
            moment = np.zeros(3)
            for n in self.desc[name]:
                force = np.array([0., 0., -GRAVITY*self.links[n]['mass']])
                moment += np.cross(coms[n]-pivots[name], force)
            holding[name] = float(-axes[name] @ moment)
            actuator, factor = self.input_dependency(name)
            independent[actuator] = independent.get(actuator, 0.)+factor*holding[name]
        return {'transforms': transforms, 'pivots': pivots, 'axes': axes,
                'coms': coms, 'com': weighted/self.mass, 'holding': holding,
                'independent_holding': independent, 'potential': weighted[2]*GRAVITY}

    def wheel_contact(self, name, state):
        wheels = [c for c in self.links[name]['xml'].findall('collision') if c.find('geometry/cylinder') is not None]
        if len(wheels) != 1:
            raise ValueError(f'Expected one wheel cylinder for {name}')
        c = wheels[0]
        radius = float(c.find('geometry/cylinder').get('radius'))
        transform = state['transforms'][name] @ origin(c.find('origin'))
        if abs(transform[2, 2]) > 1e-9:
            raise ValueError('Contact approximation requires horizontal wheel axle')
        return transform[:3, 3]-[0., 0., radius]


def radical_inverse(index, base):
    value, factor = 0., 1./base
    while index:
        index, digit = divmod(index, base)
        value += digit*factor
        factor /= base
    return value


def configurations(model, count):
    names = model.arm_inputs
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    if len(names) > len(primes):
        raise ValueError('Add more prime bases for this robot')
    limits = np.array([[model.joints[n]['lower'], model.joints[n]['upper']] for n in names])
    if not np.isfinite(limits).all():
        raise ValueError('All sampled independent arm joints need finite limits')
    yield 'zero', dict.fromkeys(names, 0.)
    targeted = [limits[:, 0], limits[:, 1], limits[np.arange(len(names)), np.arange(len(names)) % 2],
                limits[np.arange(len(names)), 1-np.arange(len(names)) % 2]]
    for k in range(len(names)):
        for bound in (0, 1):
            v = np.zeros(len(names))
            v[k] = limits[k, bound]
            targeted.append(v)
    emitted = 1
    for i, v in enumerate(targeted):
        if emitted == count:
            return
        yield f'limit_probe_{i}', dict(zip(names, map(float, v)))
        emitted += 1
    for i in range(1, count-emitted+1):
        # Halton starts after a fixed 31-index skip; all twelve arm inputs vary.
        u = np.array([radical_inverse(i+31, p) for p in primes[:len(names)]])
        yield f'halton_{i+31}', dict(zip(names, map(float, limits[:, 0]+u*(limits[:, 1]-limits[:, 0]))))


def rotate_xy(v, cosine, sine):
    return np.column_stack((v[0]*cosine-v[1]*sine, v[0]*sine+v[1]*cosine))


def support_audit(model, state, angles):
    a = model.wheel_contact('right_wheel', state)
    b = model.wheel_contact('left_wheel', state)
    c = model.wheel_contact('caster_link', state)
    if max(abs(v[2]) for v in (a, b, c)) > 1e-9:
        raise ValueError('Nominal contact points are not on z=0')
    pivot = state['pivots']['caster_swivel_joint']
    axis = state['axes']['caster_swivel_joint']
    if not np.allclose(axis, [0., 0., 1.], atol=1e-9):
        raise ValueError('Continuous caster bound requires a vertical swivel axis')
    if abs(a[0]-b[0]) > 1e-9 or b[1] <= a[1] or pivot[0] <= a[0]:
        raise ValueError('Unexpected rear support geometry; review support orientation')
    rotating_mass_vector = sum((model.links[n]['mass']*(state['coms'][n]-pivot)[:2]
                                for n in model.desc['caster_swivel_joint']), np.zeros(2))/model.mass
    g0 = state['com'][:2]-rotating_mass_vector
    trail_vector = c[:2]-pivot[:2]
    trail = float(np.linalg.norm(trail_vector))
    cos, sin = np.cos(angles), np.sin(angles)
    g = g0+rotate_xy(rotating_mass_vector, cos, sin)
    front = pivot[:2]+rotate_xy(trail_vector, cos, sin)
    # Counterclockwise support triangle: right rear -> caster -> left rear.
    e1, h1 = front-a[:2], g-a[:2]
    e2, h2 = b[:2]-front, g-front
    m1 = (e1[:, 0]*h1[:, 1]-e1[:, 1]*h1[:, 0])/np.linalg.norm(e1, axis=1)
    m2 = (e2[:, 0]*h2[:, 1]-e2[:, 1]*h2[:, 0])/np.linalg.norm(e2, axis=1)
    m3 = g[:, 0]-a[0]
    margins = np.column_stack((m1, m2, m3))
    index, edge = np.unravel_index(np.argmin(margins), margins.shape)
    amplitude = float(np.linalg.norm(rotating_mass_vector))
    # For a fixed rear anchor R, d(theta)=n(theta).(G(theta)-R).
    # |d'| <= |G'| + |C'|*|G-R|/|C-R|. Circle bounds give
    # |G'|<=amplitude, |C'|=trail, |G-R|<=|g0-R|+amplitude,
    # |C-R|>=|pivot-R|-trail. Rear-edge derivative <=amplitude.
    lipschitz = [amplitude+trail*(np.linalg.norm(g0-r[:2])+amplitude)/
                 (np.linalg.norm(pivot[:2]-r[:2])-trail) for r in (a, b)] + [amplitude]
    error_bound = max(lipschitz)*math.pi/len(angles)
    sampled_minimum = float(margins[index, edge])
    return {'sampled_margin_m': sampled_minimum,
            'continuous_angle_lower_bound_m': sampled_minimum-error_bound,
            'angular_discretization_bound_m': error_bound,
            'caster_angle_rad': float(angles[index]),
            'edge': ['right_rear_to_caster', 'caster_to_left_rear', 'rear_axle'][edge],
            'com_at_sampled_minimum_m': [*map(float, g[index]), float(state['com'][2])],
            'contacts_at_sampled_minimum_m': [a.tolist(), [*front[index].tolist(), 0.], b.tolist()]}


def verify_caster_circle(model):
    """Check the analytical caster/COM circle against separate full FK calls."""
    initial = model.evaluate({})
    pivot = initial['pivots']['caster_swivel_joint']
    k = sum((model.links[n]['mass']*(initial['coms'][n]-pivot)[:2]
             for n in model.desc['caster_swivel_joint']), np.zeros(2))/model.mass
    g0 = initial['com'][:2]-k
    c0 = model.wheel_contact('caster_link', initial)[:2]-pivot[:2]
    errors, contact_errors = [], []
    for angle in np.linspace(-math.pi, math.pi, 113):
        state = model.evaluate({'caster_swivel_joint': float(angle)})
        cos, sin = np.array([math.cos(angle)]), np.array([math.sin(angle)])
        expected_com = g0+rotate_xy(k, cos, sin)[0]
        expected_contact = pivot[:2]+rotate_xy(c0, cos, sin)[0]
        errors.append(float(np.linalg.norm(state['com'][:2]-expected_com)))
        contact_errors.append(float(np.linalg.norm(model.wheel_contact('caster_link', state)[:2]-expected_contact)))
        errors.append(abs(float(state['com'][2]-initial['com'][2])))
    if max(errors+contact_errors) > 1e-10:
        raise ValueError('Full FK disagrees with analytical caster-circle model')
    return {'caster_circle_full_fk_checks': 113,
            'maximum_caster_circle_COM_error_m': max(errors),
            'maximum_caster_circle_contact_error_m': max(contact_errors)}


def markdown(report):
    s, v = report['support'], report['validation']
    lines = ['# Independent static physics audit', '',
             f"URDF SHA-256: `{report['urdf_sha256']}`", '',
             f"Model mass: **{report['mass_kg']:.6f} kg**. Gravity: {GRAVITY} m/s². No added payload.", '',
             f"Evaluated {report['samples']['arm_pose_count']} simultaneous arm configurations, including zero, limit probes and a deterministic Halton sequence.",
             f"For every sampled arm pose, evaluated {report['samples']['caster_grid_angles']} full-circle caster angles and used a derivative bound to cover the angles between samples.", '',
             f"Minimum sampled support margin: **{1000*s['minimum_sampled_margin_m']:.3f} mm**.",
             f"Guaranteed lower bound across the full caster rotation, for these sampled arm poses: **{1000*s['minimum_continuous_angle_lower_bound_m']:.3f} mm**.",
             f"Support status: **{s['status']}**. This is a level-ground point-contact calculation, not a dynamic tip test or an exhaustive arm-workspace proof.", '',
             '| Independent input | Max absolute no-load holding torque (Nm) | URDF effort (Nm) | Samples over effort |',
             '|---|---:|---:|---:|']
    for name, entry in report['actuators'].items():
        lines.append(f"| {name} | {entry['maximum_absolute_holding_torque_Nm']:.6f} | {entry['urdf_effort_Nm']:.6f} | {entry['samples_exceeding_effort']} |")
    lines += ['', f"Effort status: **{report['effort_status']}**. URDF efforts are provisional modelling values; these results do not establish the servo kit's rated or continuous capacity.", '',
              'Mimic jaw torques are combined by virtual work: input torque equals the driven jaw torque plus multiplier × mimicked jaw torque. Individual jaw-coordinate moments are retained in the JSON.', '',
              f"Independent central-difference potential-energy check: {v['finite_difference_coordinates_checked']} coordinate evaluations; maximum error {v['maximum_gravity_gradient_error_Nm']:.3g} Nm.", '',
              'The computation reads masses and COM origins from the URDF inertials. Inertia tensors are checked for positive definiteness; static gravity requires mass and COM, not the rotational tensor values.', '',
              '## Scope and limits', '']
    lines += [f'- {x}' for x in report['limitations']]
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    package = Path(__file__).resolve().parents[1]
    parser.add_argument('--urdf', type=Path, default=package/'urdf/underbot.urdf')
    parser.add_argument('--samples', type=int, default=2000)
    parser.add_argument('--caster-angles', type=int, default=720)
    parser.add_argument('--output', type=Path, default=package/'validation/static_physics.json')
    args = parser.parse_args()
    if args.samples < 30 or args.caster_angles < 36:
        parser.error('Use at least 30 arm samples and 36 caster angles')
    model = Model(args.urdf)
    caster_verification = verify_caster_circle(model)
    angles = np.arange(args.caster_angles)*2.*math.pi/args.caster_angles
    actuator_names = [n for n in model.moving if model.joints[n]['mimic'] is None and n not in ('caster_swivel_joint', 'caster_wheel_joint')]
    stats = {n: {'urdf_effort_Nm': model.joints[n]['effort'], 'maximum_absolute_holding_torque_Nm': 0.,
                 'samples_exceeding_effort': 0, 'worst_pose': None} for n in actuator_names}
    raw_max = {n: 0. for n in model.moving}
    com_min, com_max = np.full(3, np.inf), np.full(3, -np.inf)
    worst_support = None
    minimum_lower = math.inf
    failed_support = 0
    zero = None
    difference_errors = []
    for sample, (label, q) in enumerate(configurations(model, args.samples)):
        state = model.evaluate(q)
        com_min, com_max = np.minimum(com_min, state['com']), np.maximum(com_max, state['com'])
        if sample == 0:
            zero = {'com_m': state['com'].tolist(), 'independent_holding_Nm': state['independent_holding']}
        for n in model.moving:
            raw_max[n] = max(raw_max[n], abs(state['holding'][n]))
        for name in actuator_names:
            torque = abs(state['independent_holding'][name])
            entry = stats[name]
            if torque > entry['maximum_absolute_holding_torque_Nm']:
                entry.update(maximum_absolute_holding_torque_Nm=torque, worst_pose={'label': label, 'joint_positions_rad': q})
            entry['samples_exceeding_effort'] += int(torque > entry['urdf_effort_Nm']+1e-9)
        support = support_audit(model, state, angles)
        minimum_lower = min(minimum_lower, support['continuous_angle_lower_bound_m'])
        if support['continuous_angle_lower_bound_m'] <= 0.:
            failed_support += 1
        if worst_support is None or support['sampled_margin_m'] < worst_support['sampled_margin_m']:
            worst_support = {**support, 'arm_pose': {'label': label, 'joint_positions_rad': q}}
        if sample in (0, 29, 211, 701, 1501, 1999):
            for name in model.arm_inputs:
                h = 1e-6
                low, high = dict(q), dict(q)
                low[name] -= h
                high[name] += h
                numeric = (model.evaluate(high)['potential']-model.evaluate(low)['potential'])/(2*h)
                difference_errors.append(abs(numeric-state['independent_holding'][name]))
    if len(difference_errors) == 0 or max(difference_errors) > 1e-6:
        raise ValueError('Independent potential-energy gradient did not match gravity torques')
    report = {
        'scope': 'URDF-only static, no-load, level-ground model audit; no simulator execution',
        'urdf_sha256': hashlib.sha256(model.raw).hexdigest(), 'gravity_m_s2': GRAVITY, 'mass_kg': model.mass,
        'samples': {'arm_pose_count': sample+1, 'caster_grid_angles': args.caster_angles,
                    'arm_sequence': 'zero, 28 targeted limit probes, Halton indices 32 onward in 12 prime bases',
                    'caster_coverage': 'full [0,2*pi) plus analytic derivative bound between grid angles'},
        'zero_pose': zero, 'com_range_at_zero_caster_m': {'min': com_min.tolist(), 'max': com_max.tolist()},
        'actuators': stats, 'individual_coordinate_maximum_absolute_holding_Nm': raw_max,
        'effort_status': 'EXCEEDANCE' if any(v['samples_exceeding_effort'] for v in stats.values()) else 'WITHIN_PROVISIONAL_LIMITS_IN_SAMPLES',
        'support': {'status': 'POSITIVE_FOR_SAMPLED_ARM_POSES_AT_ALL_CASTER_ANGLES' if failed_support == 0 else 'NOT_ESTABLISHED',
                    'minimum_sampled_margin_m': worst_support['sampled_margin_m'],
                    'minimum_continuous_angle_lower_bound_m': minimum_lower,
                    'arm_poses_without_positive_continuous_angle_bound': failed_support,
                    'worst_sampled_case': worst_support},
        'validation': {'finite_difference_coordinates_checked': len(difference_errors),
                       'maximum_gravity_gradient_error_Nm': max(difference_errors), **caster_verification},
        'limitations': [
            'All mass/COM, arm geometry, motor limits and contact dimensions inherit the model\'s unmeasured hardware assumptions. Positive numerical results cannot verify actual hardware.',
            'Arm-space sampling does not prove extrema across every allowed simultaneous pose. Limit probes and Halton points improve coverage but are not a continuous workspace bound.',
            'No payload, inertial acceleration, slopes, traction, braking, servo friction, gearbox efficiency, cable loads, battery sag, thermal duty, collision validity, or control tracking is included.',
            'Support uses the centers of three ideal tire contacts on a rigid level plane. No suspension, tire deformation or uneven-ground model is used.',
            'Holding torque is a static actuator-input requirement. Mimic coupling uses ideal, unit-efficiency virtual work; real linkage transmission is unmeasured.',
            'Passive caster moments are reported as coordinates and are not interpreted as commanded actuator capacities.',
            'No Gazebo, Isaac Sim, Isaac Lab, RViz, ros2_control, USD importer, or hardware test is performed by this script.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    args.output.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({'samples': sample+1, 'mass_kg': model.mass,
                      'minimum_support_margin_lower_bound_mm': minimum_lower*1000.,
                      'effort_status': report['effort_status'],
                      'max_gradient_error_Nm': max(difference_errors)}, indent=2))
    return 0 if failed_support == 0 and report['effort_status'] != 'EXCEEDANCE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
