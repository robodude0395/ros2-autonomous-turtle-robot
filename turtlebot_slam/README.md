# turtlebot_slam

SLAM mapping package — drive the robot around to build and save a map of the room.

## Overview

Uses `slam_toolbox` (online async mode) with the Kinect 360 depth image converted to a 2D LaserScan. You drive the robot manually with `teleop_twist_keyboard` while the map builds in real-time.

## Prerequisites

On the Ubuntu VM:
```bash
sudo apt install -y ros-kilted-slam-toolbox ros-kilted-nav2-map-server ros-kilted-nav2-lifecycle-manager ros-kilted-depthimage-to-laserscan ros-kilted-teleop-twist-keyboard
```

On the Raspberry Pi:
- micro-ROS agent running (connected to Pico)
- Kinect node running (`ros2 run kinect_ros2 kinect_ros2_node`)

## Usage

### 1. Kill any stale nodes

**Important:** Always start with a clean slate. Stale nodes from previous sessions can publish conflicting TF transforms and cause the robot to jitter erratically in RViz.

```bash
pkill -f "ros2 launch"
pkill -f diff_drive_odom
```

### 2. Start SLAM mapping

```bash
ros2 launch turtlebot_slam slam_mapping.launch.py
```

### 3. Activate slam_toolbox (lifecycle node)

In ROS 2 Kilted, `slam_toolbox` is a lifecycle node. It starts in `unconfigured` state and must be manually activated:

```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

You can verify it's active with:
```bash
ros2 lifecycle get /slam_toolbox
```

### 4. Drive the robot

In a separate terminal:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

**Mapping tips:**
- Drive slowly (< 0.2 m/s) for best results
- The Kinect has a ~57° horizontal FOV — you need to physically rotate the robot to map areas outside its view
- For small rooms, drive the robot in a slow loop around the perimeter
- The map updates as you move — watch RViz to confirm coverage

### 5. Save the map

Once you're happy with the map:
```bash
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room
```

This saves `~/maps/my_room.pgm` (image) and `~/maps/my_room.yaml` (metadata).

## TF Tree

```
map → odom → base_link → [wheels, kinect, etc.]
 (slam)  (odom node)  (robot_state_publisher)
```

## Known Issues & Troubleshooting

### Robot jitters between two positions in RViz
**Cause:** Two nodes publishing the same TF transform (e.g., a stale `diff_drive_odom` from a previous session).
**Fix:** Kill all nodes (`pkill -f "ros2 launch"`) and relaunch cleanly.

### "No map received" in RViz
**Cause:** `slam_toolbox` is in `unconfigured` state (lifecycle node not activated).
**Fix:** Run `ros2 lifecycle set /slam_toolbox configure && ros2 lifecycle set /slam_toolbox activate`

### Map doesn't expand when rotating in place
**Cause:** `slam_toolbox` uses `minimum_travel_distance` AND `minimum_travel_heading` — both must be exceeded. Pure rotation with very small odom changes may not trigger new nodes.
**Fix:** Drive the robot forward slightly (even a few cm) between rotations to trigger map updates.

### Fixed frame "odom" or "map" not found in RViz
**Cause:** The odom node hasn't received encoder data yet.
**Fix:** Ensure the micro-ROS agent is running on the Pi and encoder topics are publishing (`ros2 topic hz /wheel/left/encoder`).

## Tuning Tips

- If the map drifts, reduce driving speed
- `link_match_minimum_response_fine` (default 0.5) controls scan match quality threshold — higher = more stable but may reject valid matches
- `correlation_search_space_dimension` (default 0.3) limits how far the scan matcher looks — smaller = less jumping but may fail in featureless areas
- The Kinect has a 0.45m minimum range — don't drive too close to walls during mapping
- `scan_height: 10` in depthimage_to_laserscan gives a tight horizontal slice — increase if you're missing obstacles, decrease if you get floor/ceiling noise
