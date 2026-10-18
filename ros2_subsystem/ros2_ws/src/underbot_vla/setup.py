from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'underbot_vla'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Athul C S',
    maintainer_email='underbot@robotics.local',
    description='Vision-Language-Action node for Compact Lab Rover',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vla_node = underbot_vla.vla_node:main',
            'chat_cli = underbot_vla.chat_cli:main',
        ],
    },
)
