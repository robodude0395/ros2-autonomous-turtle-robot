# turtlebot_navigation

Nav2 autonomous navigation — send the robot to goals and it navigates there while avoiding obstacles.

## Overview

Two modes of operation:

1. **Map-based navigation** (`navigation.launch.py`) — Uses a pre-built map + AMCL localization. Best for known environments.
2. **SLAM navigation** (`slam_navigation.launch.py`) — Builds the map while navigating. No pre-built map needed. Best for exploration or changing environments.

## Prerequisites

On the Ubuntu VM:
```bash
sudo apt install -y ros-kilted-navigation2 ros-kilted-nav2-bringup ros-kilted-slam-toolbox ros-kilted-depthimage-to-laserscan
```

A saved map (from `turtlebot_slam`) is required for map-based navigation.

## Usage

### Option A: Navigate with a saved map

```bash
# Kill any previous sessions first!
pkill -f "ros2 launch"

# Launch Nav2 with your map
ros2 launch turtlebot_navigation navigation.launch.py map:=$HOME/maps/my_room.yaml
```

In RViz:
1. Click **2D Pose Estimate** to set the robot's initial position on the map
2. Click **Nav2 Goal** to send the robot to a target pose

### Option B: Navigate while mapping (SLAM + Nav2)

```bash
pkill -f "ros2 launch"
ros2 launch turtlebot_navigation slam_navigation.launch.py
```

**Note:** You'll need to activate slam_toolbox manually:
```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

No initial pose needed — SLAM handles localization. Just click **Nav2 Goal** in RViz.

## How It Works

```
Kinect depth → LaserScan → Costmaps → Planner → Controller → cmd_vel → Motors
                              ↑
                         Map (static or SLAM)
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
| laser range | 0.45–8.0 m | Kinect 360 specs |

## Known Issues & Troubleshooting

### Robot jitters in RViz
**Cause:** Stale nodes from a previous session publishing conflicting TF transforms.
**Fix:** Always `pkill -f "ros2 launch"` before starting a new session.

### Robot won't move after setting a goal
**Cause:** Nav2 lifecycle nodes not activated.
**Fix:** Check `ros2 lifecycle list` — all nodes should be in `active` state. The lifecycle manager should handle this automatically, but if not:
```bash
ros2 lifecycle set /controller_server configure
ros2 lifecycle set /controller_server activate
# ... repeat for planner_server, behavior_server, bt_navigator
```

### Poor localization (AMCL mode)
**Fix:** Re-set initial pose in RViz with **2D Pose Estimate**. Make sure the robot's actual position matches where you place it on the map.

### Robot oscillates near goal
**Fix:** Reduce `max_vel_x` in nav2_params.yaml or increase `xy_goal_tolerance`.

### Gets stuck near obstacles
**Fix:** Increase `inflation_radius` in the costmap config.

### "Transform timeout" errors
**Cause:** The odom node or robot_state_publisher isn't keeping up.
**Fix:** Ensure no duplicate nodes are running. Check with `ros2 node list`.

## Important Notes

- **Always start clean** — kill previous sessions before launching
- The Kinect has a 0.45m minimum range — the robot can't see obstacles closer than that
- Drive slowly during initial localization to help AMCL converge
- The velocity smoother remaps `cmd_vel` → `cmd_vel_nav` internally — don't run teleop simultaneously with Nav2
