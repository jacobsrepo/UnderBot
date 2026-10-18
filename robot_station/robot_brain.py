"""Grounding and proposed task plans. This module never executes robot actions."""
import json
from pathlib import Path
import re
import subprocess


def memory_snapshot(python, config):
    if not python or not config:
        return {'available': False, 'reason': 'PostgreSQL memory is not configured.'}
    try:
        result = subprocess.run([python, str(Path(__file__).with_name('robot_memory.py')), config],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return {'available': False, 'reason': 'PostgreSQL memory helper failed.', 'error_code': 'helper_exit'}
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or not isinstance(data.get('available'), bool):
            raise ValueError('Invalid memory response')
        return data
    except subprocess.TimeoutExpired:
        return {'available': False, 'reason': 'PostgreSQL memory lookup timed out; please retry.', 'error_code': 'helper_timeout'}
    except Exception:
        return {'available': False, 'reason': 'PostgreSQL memory is unavailable.', 'error_code': 'helper_unavailable'}


def identity_answer(prompt, memory):
    match = re.fullmatch(r'\s*(?:who\s+(?:is|are)|do you know|tell me about)\s+(.+?)\s*[?.!]*\s*', prompt, re.I)
    if not match:
        return None
    query = match[1].strip(' ?.!"').casefold()
    if query in ('you', 'yourself', 'underbot'):
        return 'I am UnderBot, your ROS 2 robot assistant. I can look up enrolled people and propose tasks; physical task execution is not connected yet.'
    if not memory.get('available'):
        return 'I cannot check who that is. ' + memory.get('reason', 'PostgreSQL memory is unavailable.') + ' I will not guess their identity.'
    tokens = re.findall(r'\w+', query)
    matches = [name for name in memory.get('people', [])
               if tokens and all(t in re.findall(r'\w+', name.casefold()) for t in tokens)]
    if len(matches) == 1:
        return f"{matches[0]} is enrolled in my PostgreSQL people memory. I have no biography or current location for them. This lookup does not mean I can see them right now."
    if len(matches) > 1:
        return 'I found multiple enrolled people: ' + ', '.join(matches[:10]) + '. Please use a full name.'
    return 'I found no matching enrolled person in my PostgreSQL memory' + (' snapshot (limited to 100 entries).' if memory.get('truncated') else '.')


def fetch_plan(prompt, memory):
    match = re.fullmatch(r'\s*(?:please\s+)?bring\s+([\w -]+?)\s+(?:the|a)\s+([\w -]+?)[.!]?\s*', prompt, re.I)
    if not match:
        return None
    person, obj = (v.strip() for v in match.groups())
    known = [n for n in memory.get('people', []) if person.casefold() in (n.casefold(), n.split()[0].casefold())]
    person = known[0] if len(known) == 1 else person
    steps = [('find_object', obj), ('navigate_near', obj), ('position_for_grasp', obj),
             ('pick', obj), ('find_person', person), ('navigate_near', person), ('handover', person)]
    return {'status': 'proposed_only', 'executable': False,
            'blockers': ['Live object positions and localization unavailable', 'Nav2 executor not connected',
                         'Manipulation and handover not implemented'] + ([] if len(known) == 1 else ['Recipient is not uniquely enrolled in memory']),
            'steps': [{'step': i, 'action': action, 'target': target} for i, (action, target) in enumerate(steps, 1)]}
