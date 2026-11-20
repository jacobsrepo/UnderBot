"""Bounded, prioritized space-time planning for two simulated circular robots."""
import heapq
import math
import re

import numpy as np
from navigation_core import navigation_intent, plan_route, segment_is_free

ROBOTS = ('robot_1', 'robot_2')


def swept_distance(a, b, c, d):
    """Minimum separation during two simultaneous linear movements (not samples)."""
    p = np.asarray(a) - c
    v = np.asarray(b) - a - (np.asarray(d) - c)
    vv = float(v @ v)
    t = max(0., min(1., -float(p @ v) / vv)) if vv else 0.
    return float(np.linalg.norm(p + t * v))


def fleet_intent(text, landmarks):
    command = re.sub(r'\s+', ' ', text.strip().lower().rstrip('.!'))
    missions = {'run team demo': 'demo', 'start team demo': 'demo',
                'swap places': 'swap', 'both robots swap places': 'swap',
                'rendezvous': 'rendezvous', 'both robots rendezvous': 'rendezvous',
                'both robots return home': 'home', 'team return home': 'home'}
    if command in missions:
        return {'action': 'team_mission', 'mission': missions[command]}
    match = re.fullmatch(r'robot[ _](\d+)\s*[:,]?\s+(.+)', text.strip(), re.I)
    if not match:
        return None
    if match[1] not in ('1', '2'):
        raise ValueError('Choose robot 1 or robot 2.')
    intent = navigation_intent(match[2], landmarks)
    if not intent or intent['action'] not in ('goal', 'stop'):
        raise ValueError('Use robot 1 go to goal_a, robot 2 go to 2, 3, or robot 1 stop.')
    return {**intent, 'robot_id': 'robot_' + match[1]}


class FleetPlanner:
    def __init__(self, grid, resolution, origin=(-20., -20.), radius=.4,
                 margin=.1, horizon=500, max_expansions=150000):
        if not all(math.isfinite(v) and v > 0 for v in (resolution, radius, margin)):
            raise ValueError('Resolution, footprint radius and margin must be positive.')
        self.resolution, self.origin = resolution, origin
        self.separation = 2 * radius + margin
        self.horizon, self.max_expansions = horizon, max_expansions
        # Additional conservative footprint inflation, including unknown/map edges.
        blocked = np.asarray(grid) != 0
        padded = np.pad(blocked, math.ceil(radius / resolution) + 1, constant_values=True)
        self.grid = np.zeros_like(grid)
        n = math.ceil(radius / resolution) + 1
        for dy in range(-n, n + 1):
            for dx in range(-n, n + 1):
                if math.hypot(max(0, abs(dx)-1), max(0, abs(dy)-1))*resolution <= radius:
                    self.grid[padded[n+dy:n+dy+grid.shape[0], n+dx:n+dx+grid.shape[1]]] = 100

    def cell(self, p):
        return tuple(math.floor((p[i]-self.origin[i])/self.resolution) for i in (0, 1))

    def world(self, c):
        return tuple(self.origin[i]+(c[i]+.5)*self.resolution for i in (0, 1))

    def clear(self, a, b):
        return segment_is_free(self.grid,
            tuple((a[i]-self.origin[i])/self.resolution for i in (0, 1)),
            tuple((b[i]-self.origin[i])/self.resolution for i in (0, 1)))

    @staticmethod
    def at(path, t):
        return path[min(t, len(path)-1)]

    def reserved_clear(self, a, b, t, reserved):
        return swept_distance(a, b, self.at(reserved, t), self.at(reserved, t+1)) >= self.separation

    def route(self, start, goal, reserved=None):
        # Validate connectivity first, preventing expensive searches for static impossibilities.
        plan_route(self.grid, start, goal, self.resolution, self.origin)
        start, goal = tuple(start), tuple(goal)
        if reserved is None:
            path = plan_route(self.grid, start, goal, self.resolution, self.origin)
            result = [start]
            for a, b in zip(path, path[1:]):
                count = max(1, math.ceil(math.dist(a, b)/self.resolution))
                result.extend(tuple(a[j]+(b[j]-a[j])*i/count for j in (0, 1)) for i in range(1, count+1))
            if len(result) > self.horizon:
                raise ValueError('Route exceeds fleet planning horizon.')
            return result
        if math.dist(goal, reserved[-1]) < self.separation:
            raise ValueError('Destinations overlap another robot footprint.')
        # Time-expanded grid with wait edges. Exact start/goal are retained.
        def heuristic(p):
            return math.dist(p, goal)/(self.resolution*math.sqrt(2))
        initial = (start, 0)
        queue = [(heuristic(start), 0, start)]
        parent = {initial: None}
        expansions = 0
        while queue:
            _, t, p = heapq.heappop(queue)
            expansions += 1
            if expansions > self.max_expansions:
                raise ValueError('Fleet planning search budget exceeded; robots remain stopped.')
            if t >= self.horizon:
                continue
            if math.dist(p, goal) <= self.resolution*math.sqrt(2) and self.clear(p, goal):
                if self.reserved_clear(p, goal, t, reserved) and all(
                    self.reserved_clear(goal, goal, k, reserved) for k in range(t+1, max(t+2, len(reserved)))):
                    result = [goal]
                    state = (p, t)
                    while state is not None:
                        result.append(state[0]); state = parent[state]
                    return result[::-1]
            cx, cy = self.cell(p)
            candidates = [p] + [self.world((cx+dx, cy+dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            for q in candidates:
                state = (q, t+1)
                if state in parent or math.dist(p, q) > self.resolution*math.sqrt(2)+1e-9:
                    continue
                if self.clear(p, q) and self.reserved_clear(p, q, t, reserved):
                    parent[state] = (p, t)
                    heapq.heappush(queue, (t+1+heuristic(q), t+1, q))
        raise ValueError('No coordinated route within the planning horizon.')

    def plan(self, starts, goals, priority=ROBOTS):
        if math.dist(starts[ROBOTS[0]], starts[ROBOTS[1]]) < self.separation:
            raise ValueError('Initial robot footprints overlap.')
        errors = []
        for order in (priority, priority[::-1]):
            try:
                first, second = order
                # Idle robots reserve their position forever; they are never moved implicitly.
                if second not in goals:
                    paths = {second: [tuple(starts[second])]}
                    paths[first] = self.route(starts[first], goals[first], paths[second]) if first in goals else [tuple(starts[first])]
                else:
                    paths = {first: self.route(starts[first], goals[first]) if first in goals else [tuple(starts[first])]}
                    paths[second] = self.route(starts[second], goals[second], paths[first])
                return paths
            except ValueError as exc:
                errors.append(str(exc))
        raise ValueError(errors[-1])
