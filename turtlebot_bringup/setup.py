from setuptools import find_packages, setup

package_name = 'turtlebot_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/bringup.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Omar Veiga',
    maintainer_email='omar@todo.com',
    description='Bringup nodes for the autonomous turtlebot',
    license='MIT',
    entry_points={
        'console_scripts': [
            'encoder_to_joint_states = turtlebot_bringup.encoder_to_joint_states:main',
            'diff_drive_odom = turtlebot_bringup.diff_drive_odom:main',
        ],
    },
)
