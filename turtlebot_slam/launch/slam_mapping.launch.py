"""
Launch file for SLAM mapping with teleop.

Brings up the full pipeline for driving the robot around and building a map:
  1. robot_state_publisher (URDF → TF)
  2. encoder_to_joint_states (encoder ticks → JointState)
  3. diff_drive_odom (encoder ticks → Odometry + odom→base_link TF)
  4. depthimage_to_laserscan (Kinect depth → /scan)
  5. slam_toolbox (online async SLAM)
  6. RViz (map + laser + TF visualization)

After launching, open a separate terminal and run:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard

Drive around the room to build the map, then save it:
    ros2 launch turtlebot_slam save_map.launch.py map_name:=my_room
"""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Package directories
    desc_pkg = get_package_share_directory('turtlebot_description')
    slam_pkg = get_package_share_directory('turtlebot_slam')

    # Files
    xacro_file = os.path.join(desc_pkg, 'urdf', 'turtlebot.urdf.xacro')
    slam_params = os.path.join(slam_pkg, 'config', 'slam_toolbox_params.yaml')
    depth2scan_params = os.path.join(slam_pkg, 'config', 'depthimage_to_laserscan.yaml')
    rviz_config = os.path.join(slam_pkg, 'rviz', 'slam.rviz')

    # Process URDF
    robot_description_content = subprocess.check_output(
        ['xacro', xacro_file]
    ).decode('utf-8')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock (set true for Gazebo)'
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

        # --- SLAM Toolbox (Online Async) ---
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[
                slam_params,
                {'use_sim_time': use_sim_time},
            ],
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
