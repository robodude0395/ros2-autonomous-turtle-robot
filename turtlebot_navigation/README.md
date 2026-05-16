# turtlebot_navigation

Nav2 autonomous navigation — send the robot to goals and it navigates there while avoiding obstacles.

## Overview

Two modes of operation:

1. **SLAM navigation** (`slam_navigation.launch.py`) — Builds the map while navigating. No pre-built map needed. **Recommended for getting started.**
2. **Map-based navigation** (`navigation.launch.py`) — Uses a pre-built map + AMCL localization. Best for known environments.

## Prerequisites

On the Ubuntu VM:
```bash
sudo apt install -y ros-kilted-navigation2 ros-kilted-nav2-bringup ros-kilted-slam-toolbox ros-kilted-depthimage-to-laserscan
```

## Usage

### Always start clean

```bash
pkill -f "ros2 launch"
```

Stale nodes from previous sessions will cause TF conflicts and erratic behavior.

### Option A: SLAM Navigation (recommended)

No map needed — the robot maps and navigates simultaneously:

```bash
ros2 launch turtlebot_navigation slam_navigation.launch.py
```

Then activate slam_toolbox (lifecycle node):
```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

Wait a few seconds for the map to start building, then send a goal:
```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 0.5, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}"
```

Or use **Nav2 Goal** in RViz (click and drag on the map).

### Option B: Map-based Navigation

Requires a saved map from `turtlebot_slam`:

```bash
ros2 launch turtlebot_navigation navigation.launch.py map:=$HOME/maps/my_room.yaml
```

**Important:** After launch, wait ~10 seconds for the initial pose to be auto-published. If the costmap doesn't appear, manually publish the initial pose:

```bash
ros2 topic pub /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}" --once
```

Or click **2D Pose Estimate** in RViz and place the robot on the map.

Then send a goal:
```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}"
```

## How It Works

```
Kinect depth → LaserScan → Costmaps → Planner → Controller → cmd_vel → Motors
                              ↑
                         Map (SLAM or static)
```

- **Global planner** (NavFn): Plans the shortest path on the global costmap
- **Local controller** (DWB): Follows the path while avoiding dynamic obstacles
- **Recovery behaviors**: Spin, backup, wait — triggered when the robot gets stuck
- **Velocity smoother**: Smooths cmd_vel to prevent jerky motor commands

## Parameters

All Nav2 parameters are in `config/nav2_params.yaml`. Key values tuned for this robot:

| Parameter | Value | Why |
|-----------|-------|-----|
| max_vel_x | 0.3 m/s | EMG30 safe cruising speed |
| max_vel_theta | 0.8 rad/s | Smooth turning |
| robot_radius | 0.22 m | Slightly larger than physical for safety margin |
| inflation_radius | 0.55 m | Keeps robot away from walls |
| laser range | 0.45–4.0 m | Kinect 360 usable range |

## RViz Map Not Showing

If you can't see the map in RViz:

1. Click **Add** → **By topic** → expand `/map` → select **Map**
2. In the Map display properties, expand **Topic**
3. Change **Durability Policy** to `Transient Local`

This is required because `map_server` publishes with transient local QoS. The included rviz config should handle this automatically, but if RViz loads a cached config it may revert to volatile.

## Known Issues & Troubleshooting

### "Goal was rejected"
**Cause:** The costmaps aren't ready — `map → odom` transform doesn't exist yet.
**Fix:** Publish the initial pose (for map-based mode) or activate slam_toolbox (for SLAM mode). Wait a few seconds for costmaps to initialize.

### Robot jitters in RViz
**Cause:** Stale nodes from a previous session publishing conflicting TF transforms.
**Fix:** Always `pkill -f "ros2 launch"` before starting a new session.

### "map frame does not exist"
**Cause:** AMCL hasn't received an initial pose (map-based mode) or slam_toolbox isn't activated (SLAM mode).
**Fix:**
- Map-based: `ros2 topic pub /initialpose geometry_msgs/msg/PoseWithCovarianceStamped "{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}" --once`
- SLAM: `ros2 lifecycle set /slam_toolbox configure && ros2 lifecycle set /slam_toolbox activate`

### Costmap not publishing
**Cause:** The `map → odom → base_link` TF chain is incomplete.
**Fix:** Verify with `ros2 run tf2_ros tf2_echo map base_link`. If it fails, fix the missing transform (see above).

### Lifecycle nodes stuck in "unconfigured"
**Cause:** In ROS 2 Kilted, Nav2 and slam_toolbox are lifecycle nodes. The lifecycle manager with `bond_timeout: 0.0` handles activation, but timing issues can occur.
**Fix:** Manually activate: `ros2 lifecycle set /<node_name> configure && ros2 lifecycle set /<node_name> activate`

### Don't run teleop simultaneously with Nav2
The velocity smoother remaps `cmd_vel` — running teleop will conflict with Nav2's velocity commands.
