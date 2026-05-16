# turtlebot_bringup

Bringup package that connects real hardware data (encoder ticks from the Pico/Pi) to the robot model and visualizes it in RViz.

## What it does

The `encoder_to_joint_states` node subscribes to raw encoder tick topics from the micro-ROS firmware and converts them into `sensor_msgs/JointState` messages. `robot_state_publisher` uses those to broadcast wheel TF frames, so RViz shows the wheels spinning in real time based on actual motor movement.

## Prerequisites

- ROS 2 Kilted installed on the VM
- `turtlebot_description` package built in the same workspace
- micro-ROS agent running on the Pi with the Pico connected
- Cyclone DDS configured for VM ↔ Pi communication (see `CONTEXT/vm_and_cyclonedds_setup.md`)

## Build

```bash
cd ~/ros2_ws
colcon build --packages-select turtlebot_description turtlebot_bringup
source install/setup.bash
```

## Launch

### Visualize with real encoder data (robot connected)

Make sure the micro-ROS agent is running on the Pi first:

```bash
# On the Pi
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200
```

Then on the VM:

```bash
ros2 launch turtlebot_bringup bringup.launch.py
```

This starts:
- `robot_state_publisher` — publishes the URDF and TF tree
- `encoder_to_joint_states` — converts encoder ticks to wheel joint positions
- `rviz2` — opens with a pre-configured view of the robot

The wheels in RViz will rotate according to the actual encoder counts from the motors.

### Visualize with manual joint sliders (no hardware needed)

If you just want to inspect the URDF model without the robot connected:

```bash
ros2 launch turtlebot_description display.launch.py
```

This uses `joint_state_publisher_gui` with sliders instead of real encoder data.

## Topics

| Topic | Type | Source | Description |
|-------|------|--------|-------------|
| `/wheel/left/encoder` | `std_msgs/Int32` | Pico (via micro-ROS) | Raw left encoder ticks |
| `/wheel/right/encoder` | `std_msgs/Int32` | Pico (via micro-ROS) | Raw right encoder ticks |
| `/joint_states` | `sensor_msgs/JointState` | `encoder_to_joint_states` | Wheel positions in radians |
| `/robot_description` | `std_msgs/String` | `robot_state_publisher` | URDF XML |
| `/tf` | `tf2_msgs/TFMessage` | `robot_state_publisher` | Transform tree |

## Parameters

The `encoder_to_joint_states` node accepts:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ticks_per_revolution` | 360 | Encoder ticks per output shaft revolution (EMG30 = 360) |
| `left_joint_name` | `left_wheel_joint` | Must match the URDF joint name |
| `right_joint_name` | `right_wheel_joint` | Must match the URDF joint name |

## Kinect 360 Setup (on the Pi)

The Kinect v1 (Xbox 360) provides RGB + depth data. We use the [`kinect_ros2`](https://github.com/fadlio/kinect_ros2) driver based on `libfreenect`.

### 1. Build libfreenect from source

The Ubuntu `libfreenect-dev` apt package does **not** ship CMake config files, so you must build from source:

```bash
cd ~
git clone https://github.com/OpenKinect/libfreenect.git
cd libfreenect
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_EXAMPLES=OFF
make -j$(nproc)
sudo make install
```

### 2. Clone the ROS 2 driver

```bash
cd ~/ros2_ws/src
git clone https://github.com/fadlio/kinect_ros2.git
```

### 3. Fix the cv_bridge header for Kilted

The driver was written for Galactic. In ROS 2 Kilted the header path changed from `.h` to `.hpp`:

```bash
sed -i 's|cv_bridge/cv_bridge.h|cv_bridge/cv_bridge.hpp|g' ~/ros2_ws/src/kinect_ros2/include/kinect_ros2/kinect_ros2_component.hpp
```

### 4. Install dependencies and build

```bash
sudo apt install -y ros-kilted-cv-bridge ros-kilted-image-transport ros-kilted-camera-info-manager

cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select kinect_ros2
source install/setup.bash
```

You'll see deprecation warnings about `ament_target_dependencies()` and unused parameter warnings — these are harmless.

### 5. Set USB permissions

The Kinect needs udev rules to be accessible without root:

```bash
sudo cp ~/libfreenect/platform/linux/udev/51-kinect.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Unplug and replug the Kinect** after this step.

### 6. Run the Kinect node

```bash
ros2 run kinect_ros2 kinect_ros2_node
```

### 7. Verify topics

```bash
ros2 topic list
```

You should see:
- `/image_raw` — RGB image
- `/camera_info` — RGB camera intrinsics
- `/depth/image_raw` — Depth image (mono16)
- `/depth/camera_info` — Depth camera intrinsics

### 8. Convert depth to LaserScan (for SLAM)

Nav2 and `slam_toolbox` need a 2D `/scan` topic. Install `depthimage_to_laserscan` to convert the Kinect depth image into a virtual laser scan:

```bash
sudo apt install -y ros-kilted-depthimage-to-laserscan
```

Run it:

```bash
ros2 run depthimage_to_laserscan depthimage_to_laserscan_node \
  --ros-args \
  --remap depth:=/depth/image_raw \
  --remap depth_camera_info:=/depth/camera_info \
  -p output_frame_id:=kinect_depth_frame \
  -p scan_height:=100 \
  -p range_min:=0.45 \
  -p range_max:=10.0
```

This publishes `/scan` (`sensor_msgs/LaserScan`) which SLAM can consume directly.

### Auto-source the workspace

So you don't have to manually source every time:

```bash
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

### Kinect topics summary

| Topic | Type | Description |
|-------|------|-------------|
| `/image_raw` | `sensor_msgs/Image` | RGB camera (rgb8) |
| `/camera_info` | `sensor_msgs/CameraInfo` | RGB intrinsics |
| `/depth/image_raw` | `sensor_msgs/Image` | Depth camera (mono16) |
| `/depth/camera_info` | `sensor_msgs/CameraInfo` | Depth intrinsics |
| `/scan` | `sensor_msgs/LaserScan` | Virtual 2D scan (from depthimage_to_laserscan) |

### Kinect troubleshooting

| Problem | Fix |
|---------|-----|
| `Findlibfreenect.cmake` not found | Build libfreenect from source (step 1) |
| `FREENECT - ERROR OPEN` / segfault | Install udev rules and replug the Kinect (step 5) |
| `cv_bridge/cv_bridge.h: No such file` | Run the sed fix in step 3 |
| No depth data | Check `lsusb` shows all 3 Kinect devices (Motor, Audio, Camera) |
| Deprecation warnings during build | Harmless — the driver uses older CMake patterns |
| Kinect topics not visible (`ros2 node info` can't find node) | Add `localhost` to the peers list in `~/cyclonedds.xml` on the Pi (required when multicast is disabled) |
| LaserScan shows 0 points in RViz despite valid data | The scan's `frame_id` (`camera_depth_frame`) must exist in the URDF TF tree — see note below |
| Scan points shoot sideways instead of forward | `camera_depth_frame` must be parented to `kinect_link` with identity transform (no rotation), not to `kinect_depth_frame` |

**Important: frame_id alignment**

The `depthimage_to_laserscan` node publishes scans with `frame_id: camera_depth_frame` (inherited from the Kinect driver's depth camera_info). The URDF must include a `camera_depth_frame` link. It should be a direct child of `kinect_link` with zero offset/rotation — this ensures the scan fans out in front of the robot correctly.

---

## Troubleshooting (General)

| Problem | Fix |
|---------|-----|
| Wheels don't move in RViz | Check `/wheel/left/encoder` is being published: `ros2 topic echo /wheel/left/encoder` |
| No topics from Pi visible | Ensure Cyclone DDS is configured with `localhost` in peers on the VM |
| `/joint_states` not published | Verify `encoder_to_joint_states` node is running: `ros2 node list` |
| RViz shows no robot | Set Fixed Frame to `base_link` manually in RViz |
