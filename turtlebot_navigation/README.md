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

## Usage

### Option A: Navigate with a saved map

First, map the room using `turtlebot_slam`, then:

```bash
ros2 launch turtlebot_navigation navigation.launch.py map:=~/maps/my_room.yaml
```

In RViz:
1. Click **2D Pose Estimate** to set the robot's initial position on the map
2. Click **Nav2 Goal** to send the robot to a target pose

### Option B: Navigate while mapping (SLAM + Nav2)

```bash
ros2 launch turtlebot_navigation slam_navigation.launch.py
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

## Troubleshooting

- **Robot won't move**: Check that the lifecycle manager activated all nodes (`ros2 lifecycle list`)
- **Poor localization (AMCL)**: Re-set initial pose in RViz, or increase `max_particles`
- **Robot oscillates**: Reduce `max_vel_x` or increase `PathDist.scale`
- **Gets stuck near obstacles**: Increase `inflation_radius`
