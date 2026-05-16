"""
Launch Nav2 autonomous navigation with a pre-built map.

This is the "go to goal" mode — give the robot a pose in RViz and it
navigates there autonomously, avoiding obstacles.

Prerequisites:
  - You have already mapped the room using turtlebot_slam
  - A saved map exists at ~/maps/<map_name>.yaml

Usage:
    ros2 launch turtlebot_navigation navigation.launch.py
    ros2 launch turtlebot_navigation navigation.launch.py map:=/path/to/my_map.yaml
"""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue


def generate_launch_description():
    # Package directories
    desc_pkg = get_package_share_directory('turtlebot_description')
    nav_pkg = get_package_share_directory('turtlebot_navigation')
    slam_pkg = get_package_share_directory('turtlebot_slam')

    # Files
    xacro_file = os.path.join(desc_pkg, 'urdf', 'turtlebot.urdf.xacro')
    nav2_params = os.path.join(nav_pkg, 'config', 'nav2_params.yaml')
    depth2scan_params = os.path.join(slam_pkg, 'config', 'depthimage_to_laserscan.yaml')
    rviz_config = os.path.join(nav_pkg, 'rviz', 'navigation.rviz')
    default_map = os.path.join(os.path.expanduser('~'), 'maps', 'my_room.yaml')

    # Process URDF
    robot_description_content = subprocess.check_output(
        ['xacro', xacro_file]
    ).decode('utf-8')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')
    map_file = LaunchConfiguration('map')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock'
        ),
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Full path to the map yaml file'
        ),

        # --- Robot State Publisher ---
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description_content,
                'use_sim_time': use_sim_time,
            }],
            output='screen'
        ),

        # --- Encoder → JointState ---
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

        # --- Differential Drive Odometry ---
        Node(
            package='turtlebot_bringup',
            executable='diff_drive_odom',
            parameters=[{
                'ticks_per_revolution': 360,
                'wheel_radius': 0.05,
                'wheel_separation': 0.38,
                'odom_frame': 'odom',
                'base_frame': 'base_link',
                'publish_tf': True,
            }],
            output='screen'
        ),

        # --- Depth Image → LaserScan ---
        Node(
            package='depthimage_to_laserscan',
            executable='depthimage_to_laserscan_node',
            remappings=[
                ('depth', '/depth/image_raw'),
                ('depth_camera_info', '/depth/camera_info'),
            ],
            parameters=[depth2scan_params],
            output='screen'
        ),

        # --- Nav2 Map Server ---
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            parameters=[{
                'yaml_filename': ParameterValue(map_file, value_type=str),
                'use_sim_time': use_sim_time,
                'topic_name': 'map',
                'frame_id': 'map',
            }],
            output='screen'
        ),

        # --- Nav2 AMCL (localization) ---
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            parameters=[nav2_params, {
                'use_sim_time': use_sim_time,
                'set_initial_pose': True,
                'initial_pose_x': 0.0,
                'initial_pose_y': 0.0,
                'initial_pose_yaw': 0.0,
            }],
            output='screen'
        ),

        # --- Nav2 Controller Server ---
        Node(
            package='nav2_controller',
            executable='controller_server',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            output='screen'
        ),

        # --- Nav2 Planner Server ---
        Node(
            package='nav2_planner',
            executable='planner_server',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            output='screen'
        ),

        # --- Nav2 Behavior Server (recoveries) ---
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            output='screen'
        ),

        # --- Nav2 BT Navigator ---
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            output='screen'
        ),

        # --- Nav2 Velocity Smoother ---
        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            name='velocity_smoother',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            remappings=[
                ('cmd_vel', 'cmd_vel_nav'),
                ('cmd_vel_smoothed', 'cmd_vel'),
            ],
            output='screen'
        ),

        # --- Nav2 Lifecycle Manager ---
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'bond_timeout': 0.0,
                'node_names': [
                    'map_server',
                    'amcl',
                    'controller_server',
                    'planner_server',
                    'behavior_server',
                    'bt_navigator',
                    'velocity_smoother',
                ],
            }],
            output='screen'
        ),

        # --- RViz ---
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),
    ])
