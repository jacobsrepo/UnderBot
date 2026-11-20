"""Preflight complete, bounded team missions before changing live simulation state."""
import math
from fleet_core import ROBOTS

MISSION_NAMES = {'demo': 'Cross, swap, rendezvous and return home',
                 'swap': 'Swap places', 'rendezvous': 'Rendezvous', 'home': 'Return home'}


def meeting_area(planner, homes):
    """Find a nearby clear square on the inflated map; never invent a free area."""
    base = homes[ROBOTS[0]]
    half = max(1.2, planner.separation*1.5)
    for dx, dy in ((half, half), (-half, half), (half, -half), (-half, -half),
                   (3*half, half), (half, 3*half), (-3*half, half), (half, -3*half)):
        cx, cy = base[0]+dx, base[1]+dy
        # Check the entire square, not just its perimeter.
        rows = math.ceil(2*half/planner.resolution)
        if all(planner.clear((cx-half, cy-half+2*half*i/rows),
                             (cx+half, cy-half+2*half*i/rows)) for i in range(rows+1)):
            return (cx, cy), half
    raise ValueError('No clear nearby team demonstration area fits both robots.')


def prepare_mission(kind, planner, positions, homes):
    if kind not in MISSION_NAMES:
        raise ValueError('Choose demo, swap, rendezvous or home.')
    stages = []
    def add(label, points):
        stages.append({'name': label, 'goals': dict(zip(ROBOTS, points))})
    if kind == 'home':
        add('Return home', [homes[n] for n in ROBOTS])
    elif kind == 'swap':
        add('Swap places', [positions[n] for n in reversed(ROBOTS)])
    else:
        (cx, cy), half = meeting_area(planner, homes)
        if kind == 'demo':
            add('Get into position', [(cx-half, cy), (cx, cy-half)])
            add('Cross paths', [(cx+half, cy), (cx, cy+half)])
            add('Swap places', [(cx, cy+half), (cx+half, cy)])
        offset = planner.separation*.75
        add('Rendezvous', [(cx-offset, cy), (cx+offset, cy)])
        if kind == 'demo':
            add('Return home', [homes[n] for n in ROBOTS])
    starts = dict(positions)
    for i, stage in enumerate(stages):
        stage['paths'] = planner.plan(starts, stage['goals'], ROBOTS if i % 2 == 0 else ROBOTS[::-1])
        starts = stage['goals']
    return stages
