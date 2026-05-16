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

**Critical:** Always start with a clean slate. Stale nodes from previous sessions publish conflicting TF transforms and cause the robot to jitter erratically in RViz.

```bash
pkill -f "ros2 launch"
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

Verify it's active:
```bash
ros2 lifecycle get /slam_toolbox
# Should show: active [3]
```

### 4. Drive the robot

In a separate terminal:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

**Mapping tips:**
- Drive slowly (< 0.2 m/s) for best results
- The Kinect has a ~57° horizontal FOV — rotate the robot to map areas outside its view
- For small rooms, drive the robot in a slow loop around the perimeter
- The map updates as you move — watch RViz to confirm coverage
- Pure rotation in place may not trigger map updates — drive forward slightly between rotations

### 5. Save the map

Once you're happy with the map:
```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room
```

This saves `~/maps/my_room.pgm` (image) and `~/maps/my_room.yaml` (metadata).

**Note:** Do NOT use the `save_map.launch.py` — use the CLI directly as shown above.

## TF Tree

```
map → odom → base_link → [wheels, kinect, etc.]
 (slam)  (odom node)  (robot_state_publisher)
```

## RViz Map Not Showing

If you see "No map received" in RViz:

1. First check that slam_toolbox is activated (`ros2 lifecycle get /slam_toolbox` should say `active [3]`)
2. If active but map still not visible: click on the Map display → expand **Topic** → change **Durability Policy** to `Transient Local`

The map_server and slam_toolbox publish with transient local QoS which requires matching subscriber settings.

## Known Issues & Troubleshooting

### Robot jitters between two positions in RViz
**Cause:** Two nodes publishing the same TF transform (stale node from a previous session).
**Fix:** Kill all nodes (`pkill -f "ros2 launch"`) and relaunch cleanly.

### "No map received" in RViz
**Cause:** Either slam_toolbox isn't activated, or RViz QoS mismatch.
**Fix:** Activate slam_toolbox, then check RViz Map display Durability Policy is `Transient Local`.

### Map doesn't expand when rotating in place
**Cause:** `slam_toolbox` requires both `minimum_travel_distance` AND `minimum_travel_heading` to be exceeded before adding new nodes. Pure rotation with near-zero translation may not trigger.
**Fix:** Drive the robot forward slightly (even a few cm) between rotations.

### Fixed frame "map" not found in RViz
**Cause:** slam_toolbox not activated — it provides the `map → odom` transform.
**Fix:** `ros2 lifecycle set /slam_toolbox configure && ros2 lifecycle set /slam_toolbox activate`

### Firmware build fails in colcon
**Cause:** The `firmware/` directory contains Pico SDK code not meant for the VM.
**Fix:** Ensure `firmware/COLCON_IGNORE` exists (committed in repo). If missing: `touch ~/ros2_ws/src/ros2_autonomous_turtlebot/firmware/COLCON_IGNORE`

## Tuning Tips

- If the map drifts, reduce driving speed
- `link_match_minimum_response_fine` (0.5) — scan match quality threshold. Higher = more stable but may reject valid matches
- `correlation_search_space_dimension` (0.3) — limits scan matcher search range. Smaller = less jumping
- `max_laser_range` (4.0m) — Kinect is noisy beyond 4m, readings are clipped
- `scan_height` (10) in depthimage_to_laserscan — narrow horizontal slice avoids floor/ceiling noise
- The Kinect has a 0.45m minimum range — don't drive too close to walls
