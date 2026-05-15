"""Launch the encoder_to_joint_states node alongside robot_state_publisher and RViz."""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    desc_pkg = get_package_share_directory('turtlebot_description')
    xacro_file = os.path.join(desc_pkg, 'urdf', 'turtlebot.urdf.xacro')
    rviz_config = os.path.join(desc_pkg, 'rviz', 'display.rviz')

    robot_description_content = subprocess.check_output(
        ['xacro', xacro_file]
    ).decode('utf-8')

    return LaunchDescription([
        # Robot state publisher (URDF → TF)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description_content}],
            output='screen'
        ),

        # Encoder ticks → JointState
        Node(
            package='turtlebot_bringup',
            executable='encoder_to_joint_states',
            parameters=[{
                'ticks_per_revolution': 360,
                'left_joint_name': 'left_wheel_joint',
                'right_joint_name': 'right_wheel_joint',
            }],
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
