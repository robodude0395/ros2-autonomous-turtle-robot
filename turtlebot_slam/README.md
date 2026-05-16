# turtlebot_slam

SLAM mapping package — drive the robot around to build and save a map of the room.

## Overview

Uses `slam_toolbox` (online async mode) with the Kinect 360 depth image converted to a 2D LaserScan. You drive the robot manually with `teleop_twist_keyboard` while the map builds in real-time.

## Prerequisites

On the Ubuntu VM:
```bash
sudo apt install -y ros-kilted-slam-toolbox ros-kilted-depthimage-to-laserscan ros-kilted-nav2-map-server ros-kilted-teleop-twist-keyboard
```

On the Raspberry Pi:
- micro-ROS agent running (connected to Pico)
- Kinect node running (`ros2 run kinect_ros2 kinect_ros2_node`)

## Usage

### 1. Start SLAM mapping

```bash
ros2 launch turtlebot_slam slam_mapping.launch.py
```

This brings up the full pipeline: URDF, odometry, depth→laser, SLAM, and RViz.

### 2. Drive the robot

In a separate terminal:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Drive slowly around the room. Watch the map build in RViz.

### 3. Save the map

Once you're happy with the map:
```bash
ros2 launch turtlebot_slam save_map.launch.py map_name:=my_room
```

This saves `~/maps/my_room.pgm` and `~/maps/my_room.yaml`.

## TF Tree

```
map → odom → base_link → [wheels, kinect, etc.]
 (slam)  (odom node)  (robot_state_publisher)
```

## Tuning Tips

- If the map drifts, reduce driving speed and increase `minimum_travel_distance` in `slam_toolbox_params.yaml`
- If loop closures fail, try increasing `loop_search_maximum_distance`
- The Kinect has a 0.45m minimum range — don't drive too close to walls during mapping
