"""Recent camera evidence, never inferred from enrollment or synthetic odometry."""
import math
import re
import threading
import time


class WorldState:
    def __init__(self, max_age=3.0):
        self.max_age = max_age
        self.lock = threading.Lock()
        self.frame = None
        self.previous = {}
        self.seen = {}

    def update(self, data, wall=None, mono=None):
        wall = time.time() if wall is None else wall
        mono = time.monotonic() if mono is None else mono
        try:
            stamp = data['header']['stamp']
            captured = int(stamp['sec']) + int(stamp['nanosec']) / 1e9
            if not math.isfinite(captured) or not 0 <= wall - captured <= self.max_age:
                return False
            objects = data['objects']
            if not isinstance(objects, list) or len(objects) > 200:
                return False
            ready = data.get('recognition_state') == 'ready'
            names, labels = {}, []
            for obj in objects:
                label = obj.get('label')
                confidence = float(obj.get('confidence', 0))
                if not isinstance(label, str) or not math.isfinite(confidence) or confidence < 0.35:
                    continue
                labels.append(label[:80])
                identity = obj.get('identity')
                if label == 'person' and ready and isinstance(identity, dict):
                    name, score = identity.get('name'), float(identity.get('similarity', 0))
                    if isinstance(name, str) and 0 < len(name) <= 120 and math.isfinite(score) and 0.5 <= score <= 1.001:
                        names[name] = score
            with self.lock:
                if self.frame and captured <= self.frame['captured']:
                    return False  # Replayed or out-of-order frames cannot renew evidence.
                confirmed = [name for name in names if name in self.previous
                             and 0 < captured - self.previous[name] <= self.max_age]
                self.previous = {name: captured for name in names}
                self.seen = {name: value for name, value in self.seen.items() if mono - value[1] <= 600}
                for name in confirmed:
                    self.seen[name] = (captured, mono)
                if len(self.seen) > 100:
                    self.seen = dict(sorted(self.seen.items(), key=lambda item: item[1][1])[-100:])
                self.frame = {'captured': captured, 'received': mono, 'labels': labels,
                              'confirmed_names': confirmed, 'candidate_names': list(names),
                              'recognition_ready': ready}
            return True
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            return False

    def snapshot(self, wall=None, mono=None):
        wall = time.time() if wall is None else wall
        mono = time.monotonic() if mono is None else mono
        with self.lock:
            frame = self.frame
            age = wall - frame['captured'] if frame else None
            fresh = bool(frame and 0 <= age <= self.max_age
                         and 0 <= mono - frame['received'] <= self.max_age)
            recent = {name: round(max(wall - stamp, mono - received), 1)
                      for name, (stamp, received) in self.seen.items()
                      if 0 <= mono - received <= 600}
            return {'source': 'EMEET camera recognition', 'fresh': fresh,
                    'capture_age_seconds': round(age, 1) if age is not None else None,
                    'recognition_ready': bool(fresh and frame['recognition_ready']),
                    'confirmed_names': frame['confirmed_names'] if fresh else [],
                    'candidate_names': frame['candidate_names'] if fresh else [],
                    'objects': frame['labels'] if fresh else [],
                    'last_seen_seconds_ago': recent,
                    'history_scope': 'confirmed observations since station startup, up to 10 minutes',
                    'positions_available': False}


def visibility_answer(prompt, memory, world):
    query = prompt.strip().rstrip('?.!').casefold()
    query = re.sub(r'\s+(?:right now|now|currently)$', '', query)
    historical = re.fullmatch(r'when (?:did you last see|was the last time you saw) (.+)', query)
    targeted = re.fullmatch(r'(?:can you see|do you see|can you recognize|do you recognize|where is) (.+)', query)
    presence = re.fullmatch(r'is (.+?) (?:here|visible|in (?:the |your )?(?:camera|view|room))', query)
    general = bool(re.search(r'\b(?:see|seeing|visible|recogniz\w*|camera|view|looking)\b', query))
    match = historical or targeted or presence
    if not match and not general:
        return None
    target = match[1] if match else None
    if target:
        target = re.sub(r'\s+in (?:the |your )?(?:camera|view|room)$', '', target)
    if target in ('me', 'anyone', 'someone', 'people', 'anything'):
        target = None
    names = memory.get('people', []) if memory.get('available') else []
    matches = [name for name in names if target and
               all(t in re.findall(r'\w+', name.casefold()) for t in re.findall(r'\w+', target))]
    if target and len(matches) > 1:
        return 'That name matches multiple enrolled people. Please use a full name: ' + ', '.join(matches[:10]) + '.'
    if target and not matches:
        return ('I cannot verify that identity because PostgreSQL memory is unavailable.' if not memory.get('available')
                else 'I have no matching enrolled identity for that name, so I cannot confirm seeing them.')
    name = matches[0] if matches else None
    past = world['last_seen_seconds_ago'].get(name) if name else None
    if historical:
        return (f'My camera last recognized {name} about {past:.0f} seconds ago. This is an observation, not a current location.'
                if past is not None else f'I have no recent confirmed sighting of {name} in this station session.')
    if not world['fresh']:
        suffix = f' The last confirmed sighting of {name} was about {past:.0f} seconds ago.' if past is not None else ''
        return "I can't tell who is visible now: no fresh camera recognition result (within 3 seconds)." + suffix
    age = world['capture_age_seconds']
    if name:
        if not world['recognition_ready']:
            return f'{name} is enrolled, but face recognition is unavailable in the latest frame. I cannot confirm seeing them.'
        if name in world['confirmed_names']:
            return f'My camera recognized {name} in consecutive frames; the latest is {age:.1f} seconds old. This is a recognition estimate, not a verified physical location.'
        if name in world['candidate_names']:
            return f'I have a possible match for {name}, but need another consistent frame before confirming.'
        return f'I do not currently recognize {name} in the camera view. They are enrolled, but that does not mean they are visible or absent from the room.'
    recognized = [name for name in world['confirmed_names'] if name in names]
    count = world['objects'].count('person')
    text = f'The latest camera result is {age:.1f} seconds old and detects {count} person(s).'
    text += (' Recognized: ' + ', '.join(recognized) + '.') if recognized else ' No enrolled identity is confirmed.'
    if not world['recognition_ready'] or not memory.get('available'):
        text += ' Identity verification is currently unavailable.'
    return text
