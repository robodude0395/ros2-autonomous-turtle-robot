"""
Save the current SLAM map to a file.

Usage:
    ros2 launch turtlebot_slam save_map.launch.py
    ros2 launch turtlebot_slam save_map.launch.py map_name:=kitchen

Saves to: <turtlebot_slam>/maps/<map_name>.pgm + .yaml
Also saves a local copy to ~/maps/<map_name> for easy access.
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    map_name = LaunchConfiguration('map_name')
    maps_dir = os.path.expanduser('~/maps')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map_name',
            default_value='my_map',
            description='Name for the saved map files (without extension)'
        ),

        # Ensure output directory exists
        ExecuteProcess(
            cmd=['mkdir', '-p', maps_dir],
            output='screen'
        ),

        # Save map using nav2_map_server's map_saver_cli
        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                '-f', [maps_dir, '/', map_name],
                '--ros-args', '-p', 'save_map_timeout:=5000',
            ],
            output='screen'
        ),
    ])
