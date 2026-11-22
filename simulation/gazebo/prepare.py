"""Prepare a local Gazebo world from R09 without modifying the source model."""
from pathlib import Path
import argparse
import copy
import xml.etree.ElementTree as ET
from arm_model import JOINT_NAMES

ROOT = Path(__file__).resolve().parent
MODEL = ROOT.parents[1] / 'models/r09/underbot_description'


def prepare(pick_place=False):
    output = ROOT / 'generated'
    output.mkdir(exist_ok=True)
    source = MODEL / 'urdf/underbot.gazebo.urdf'
    robot = ET.parse(source)
    # Native DART lacks mimic constraints. Two independent finger controllers
    # subscribe to the same target, preserving the source's 1:1 joint convention.
    for joint in robot.findall('joint'):
        mimic = joint.find('mimic')
        if mimic is None:
            continue
        leader = mimic.get('joint')
        if mimic.get('multiplier', '1') != '1' or mimic.get('offset', '0') != '0':
            raise ValueError('Only equal-angle finger coupling is supported')
        joint.remove(mimic)
        for gazebo in robot.findall('gazebo'):
            for plugin in list(gazebo.findall('plugin')):
                if plugin.findtext('joint_name') == leader:
                    follower = copy.deepcopy(plugin)
                    follower.find('joint_name').text = joint.get('name')
                    gazebo.append(follower)
                    break
    for plugin in robot.findall('.//gazebo/plugin'):
        name = plugin.findtext('joint_name')
        if name is None:
            continue
        leader = name.replace('gripper_right_joint', 'gripper_left_joint')
        if leader in JOINT_NAMES:
            plugin.find('topic').text = '/underbot/arm_targets'
            ET.SubElement(plugin, 'use_actuator_msg').text = 'true'
            ET.SubElement(plugin, 'actuator_number').text = str(JOINT_NAMES.index(leader))
    for mesh in robot.findall('.//mesh'):
        name = mesh.get('filename')
        if name.startswith('package://underbot_description/'):
            asset = MODEL / name.removeprefix('package://underbot_description/')
        else:
            asset = source.parent / name
        asset = asset.resolve()
        if not asset.is_file():
            raise FileNotFoundError(asset)
        mesh.set('filename', asset.as_posix())
    robot.write(output / 'underbot.urdf', encoding='utf-8', xml_declaration=True)
    world = ET.parse(MODEL / 'config/underbot_empty.sdf')
    # Start paused: inspect import before enabling gravity and controllers.
    include = ET.SubElement(world.getroot().find('world'), 'include')
    ET.SubElement(include, 'uri').text = (output / 'underbot.urdf').as_posix()
    ET.SubElement(include, 'name').text = 'underbot'
    ET.SubElement(include, 'pose').text = '0 0 0.002 0 0 0'
    if pick_place:
        task = ET.parse(ROOT / 'pick_place.sdf').getroot()
        for model in task:
            world.getroot().find('world').append(model)
    ET.indent(world, space='  ')
    destination = output / ('pick_place_world.sdf' if pick_place else 'underbot_world.sdf')
    world.write(destination, encoding='utf-8', xml_declaration=True)
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pick-place', action='store_true')
    prepare(parser.parse_args().pick_place)
