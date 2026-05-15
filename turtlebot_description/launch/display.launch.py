"""Launch robot_state_publisher + joint_state_publisher_gui + RViz for URDF visualization."""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_dir = get_package_share_directory('turtlebot_description')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'turtlebot.urdf.xacro')
    rviz_config = os.path.join(pkg_dir, 'rviz', 'display.rviz')

    # Process xacro at launch time to get the URDF XML string
    robot_description_content = subprocess.check_output(
        ['xacro', xacro_file]
    ).decode('utf-8')

    use_gui = LaunchConfiguration('use_gui')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gui',
            default_value='true',
            description='Launch joint_state_publisher_gui for manual joint control'
        ),

        # Publish robot description to /robot_description
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description_content
            }],
            output='screen'
        ),

        # GUI sliders to move joints (useful for testing without hardware)
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            condition=IfCondition(use_gui),
            output='screen'
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            output='screen'
        ),
    ])
