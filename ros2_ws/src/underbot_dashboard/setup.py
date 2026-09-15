from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'underbot_dashboard'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'templates'), glob('underbot_dashboard/templates/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Athul C S',
    maintainer_email='underbot@robotics.local',
    description='Web Dashboard for Compact Lab Rover',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'dashboard_server = underbot_dashboard.server:main',
        ],
    },
)
