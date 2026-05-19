"""
Launch Nav2 autonomous navigation with a pre-built map.

Classic turtlebot navigation: map + AMCL localization + costmaps + Nav2 goal planning.
Give the robot a pose in RViz and it navigates there autonomously, avoiding obstacles.

Prerequisites:
  - You have already mapped the room using turtlebot_slam
  - A saved map exists at ~/maps/<map_name>.yaml

Usage:
    ros2 launch turtlebot_navigation navigation.launch.py
    ros2 launch turtlebot_navigation navigation.launch.py map:=$HOME/maps/my_room.yaml

After launch (~10s), the map should appear in RViz. If not, publish initial pose:
    ros2 topic pub /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
      "{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}" --once
"""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
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
            }],
            output='screen'
        ),

        # --- Nav2 Controller Server ---
        # Remap cmd_vel → cmd_vel_stamped so it goes through the twist relay
        Node(
            package='nav2_controller',
            executable='controller_server',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            remappings=[('cmd_vel', 'cmd_vel_stamped')],
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
        # Remap cmd_vel → cmd_vel_stamped so recovery behaviors also go through relay
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            remappings=[('cmd_vel', 'cmd_vel_stamped')],
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
        # Reads TwistStamped from controller on cmd_vel_stamped,
        # outputs smoothed TwistStamped to cmd_vel_smoothed (for the relay node)
        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            name='velocity_smoother',
            parameters=[nav2_params, {'use_sim_time': use_sim_time}],
            remappings=[
                ('cmd_vel', 'cmd_vel_stamped'),
                ('cmd_vel_smoothed', 'cmd_vel_smoothed'),
            ],
            output='screen'
        ),

        # --- TwistStamped → Twist relay ---
        # Nav2 Kilted publishes TwistStamped; micro-ROS firmware expects Twist.
        # This node strips the header and republishes as plain Twist on /cmd_vel.
        Node(
            package='turtlebot_bringup',
            executable='twist_relay',
            parameters=[{
                'input_topic': '/cmd_vel_smoothed',
                'output_topic': '/cmd_vel',
            }],
            output='screen'
        ),

        # --- Lifecycle Manager: ALL Nav2 nodes ---
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

        # --- Publish initial pose at 10s (AMCL needs this to start map→odom TF) ---
        TimerAction(
            period=10.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        'ros2', 'topic', 'pub', '/initialpose',
                        'geometry_msgs/msg/PoseWithCovarianceStamped',
                        '{header: {frame_id: "map"}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}',
                        '--times', '5',
                    ],
                    output='screen'
                ),
            ]
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
