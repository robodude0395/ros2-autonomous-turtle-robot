# Navigation Debug Context — Carry Forward to Next Session

## Project Overview
ROS 2 Kilted autonomous turtlebot. Differential drive with MD25/EMG30 motors, Raspberry Pi Pico (micro-ROS firmware), Kinect 360 for depth, Ubuntu VM (UTM on Mac) for ROS 2 processing.

## Architecture
- **Pi**: micro-ROS agent + Kinect node → publishes `/wheel/left/encoder`, `/wheel/right/encoder`, `/depth/image_raw`, `/depth/camera_info`
- **VM**: All ROS 2 processing — odometry, SLAM, Nav2, RViz
- **Communication**: CycloneDDS over bridged networking

## What Works
- ✅ SLAM mapping (`ros2 launch turtlebot_slam slam_mapping.launch.py`) — after manually activating slam_toolbox lifecycle
- ✅ Map saving (`ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room`)
- ✅ Odometry (`diff_drive_odom` node) — stable, no jitter when started clean
- ✅ `/scan` topic at ~30-38Hz from depthimage_to_laserscan (frame: `camera_depth_frame`)
- ✅ TF chain: `map → odom → base_link → camera_depth_frame` — all verified working
- ✅ Map server active, publishing `/map` with transient_local QoS
- ✅ AMCL active, publishing `map → odom` after receiving initial pose
- ✅ All Nav2 lifecycle nodes (controller_server, planner_server, bt_navigator, etc.) in `active` state
- ✅ `/local_costmap/local_costmap` lifecycle node is `active`
- ✅ `/global_costmap/global_costmap` lifecycle node is `active`
- ✅ Map visible in RViz (after manually adding Map display with Transient Local durability)

## The Unsolved Problem
**Costmaps are active but NOT publishing.** Both `/local_costmap/costmap` and `/global_costmap/costmap` topics exist but have zero publish rate. No error messages in `/rosout` related to costmaps.

### What was verified:
- `/scan` is flowing at ~37Hz
- Scan frame is `camera_depth_frame`
- TF `odom → camera_depth_frame` resolves successfully
- TF `map → base_link` resolves successfully
- `controller_server` is active (owns local costmap)
- `planner_server` is active (owns global costmap)
- No error logs from costmap nodes
- Goal sent via action was **rejected** (because costmaps aren't ready)

### Likely root cause (not yet confirmed):
The costmap obstacle layer subscribes to `/scan` and tries to transform each scan message using the TF at the scan's timestamp. If there's a **timestamp mismatch** between the scan messages and the TF data (e.g., the Kinect/depthimage_to_laserscan uses wall clock but the odom TF uses a slightly different time source), the transform lookup fails silently and the costmap never processes any observations, so it never publishes.

### Things to investigate next:
1. **Timestamp comparison**: Compare `ros2 topic echo /scan --once | grep stamp` with `ros2 topic echo /tf --once | grep stamp` — are they using the same clock?
2. **Try increasing `transform_tolerance`** in the costmap config (currently not explicitly set, defaults to 0.3s). Set it to something large like 5.0 to see if that fixes it.
3. **Check if `use_sim_time: false`** is consistent everywhere — if any node uses sim time while others don't, timestamps won't match.
4. **Try running nav2 with the standard nav2_bringup launch** to see if it's a config issue: `ros2 launch nav2_bringup navigation_launch.py map:=$HOME/maps/my_room.yaml use_sim_time:=false`
5. **Check observation_sources config** — the costmap expects `scan` topic with `data_type: "LaserScan"`. Verify the topic name matches exactly.

## Key Config Files
- Nav2 params: `turtlebot_navigation/config/nav2_params.yaml`
- Depth2scan params: `turtlebot_slam/config/depthimage_to_laserscan.yaml`
- SLAM params: `turtlebot_slam/config/slam_toolbox_params.yaml`
- Navigation launch: `turtlebot_navigation/launch/navigation.launch.py`

## Costmap Config (from nav2_params.yaml)
```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 5.0
      publish_frequency: 2.0
      global_frame: odom
      robot_base_frame: base_link
      rolling_window: true
      width: 3
      height: 3
      resolution: 0.05
      robot_radius: 0.22
      plugins: ["obstacle_layer", "inflation_layer"]
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: true
        observation_sources: scan
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          clearing: true
          marking: true
          data_type: "LaserScan"
          raytrace_max_range: 8.0
          raytrace_min_range: 0.0
          obstacle_max_range: 7.5
          obstacle_min_range: 0.0
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
```

## Known Gotchas (solved)
1. **Lifecycle nodes**: In Kilted, slam_toolbox and all Nav2 nodes are lifecycle nodes. Need `bond_timeout: 0.0` in lifecycle manager.
2. **Stale nodes cause jitter**: Always `pkill -f "ros2 launch"` before relaunching.
3. **RViz QoS mismatch**: Map display needs `Durability Policy: Transient Local` to see `/map`.
4. **AMCL needs initial pose**: Won't publish `map → odom` until it receives `/initialpose`.
5. **Scan frame**: Kinect driver publishes depth in `camera_depth_frame` (not `kinect_depth_frame`).
6. **Firmware COLCON_IGNORE**: The `firmware/` dir needs COLCON_IGNORE to prevent colcon from trying to build Pico SDK code on the VM.
7. **map_saver_cli**: The `save_map_timeout` parameter must be a float (5000.0 not 5000).

## Packages
```
firmware/                  — Pico micro-ROS (C, not built on VM)
turtlebot_description/     — URDF (ament_cmake)
turtlebot_bringup/         — encoder_to_joint_states + diff_drive_odom (ament_python)
turtlebot_slam/            — SLAM mapping config/launch (ament_cmake)
turtlebot_navigation/      — Nav2 navigation config/launch (ament_cmake)
```
