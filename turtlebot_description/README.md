# turtlebot_description

URDF model and visualization launch files for the autonomous turtlebot.

## Package Contents

```
turtlebot_description/
├── urdf/
│   └── turtlebot.urdf.xacro    # Robot model (xacro format)
├── launch/
│   └── display.launch.py       # Launches RSP + joint GUI + RViz
├── rviz/
│   └── display.rviz            # Pre-configured RViz layout
├── CMakeLists.txt
└── package.xml
```

## Prerequisites

ROS 2 Kilted with the following packages:

```bash
sudo apt install -y ros-kilted-xacro ros-kilted-joint-state-publisher-gui ros-kilted-robot-state-publisher ros-kilted-rviz2
```

## Build

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone <your-repo-url> turtlebot

cd ~/ros2_ws
source /opt/ros/kilted/setup.bash
colcon build --packages-select turtlebot_description
source install/setup.bash
```

Add the workspace to your shell so it's always available:

```bash
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

## Launch

### Visualize with joint sliders (no hardware needed)

```bash
ros2 launch turtlebot_description display.launch.py
```

This opens RViz with the robot model and a GUI with sliders to manually rotate the wheel joints.

### Visualize without the joint GUI (when using real hardware)

```bash
ros2 launch turtlebot_description display.launch.py use_gui:=false
```

In this mode, wheel joint states come from the actual robot (via a joint_state_publisher node on the Pi).

## URDF Structure

| Link | Description |
|------|-------------|
| `base_link` | Robot centre at wheel axle height |
| `base_footprint` | Ground plane projection (used by Nav2) |
| `bottom_plate` | Lower MDF circle |
| `top_plate` | Upper MDF circle |
| `left_wheel` | Left drive wheel (continuous joint) |
| `right_wheel` | Right drive wheel (continuous joint) |
| `caster` | Passive rear support |
| `kinect_link` | Kinect sensor body |
| `kinect_depth_frame` | Optical frame (Z forward, X right, Y down) |

## Customising Dimensions

Edit the xacro properties at the top of `urdf/turtlebot.urdf.xacro`:

| Parameter | Description |
|-----------|-------------|
| `base_radius` | Radius of the MDF circles |
| `base_height` | MDF thickness |
| `base_separation` | Vertical gap between the two plates |
| `wheel_radius` | Drive wheel radius |
| `wheel_width` | Drive wheel thickness |
| `wheel_separation` | Centre-to-centre wheel distance (must match firmware) |
| `caster_radius` | Caster ball/wheel radius |
| `kinect_x_offset` | Kinect forward offset from centre |
| `kinect_z_offset` | Kinect height above top plate |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `package not found` on launch | Run `source ~/ros2_ws/install/setup.bash` |
| RViz shows nothing / white screen | Check Fixed Frame is set to `base_link` in RViz |
| RViz crashes on VM | Try `export LIBGL_ALWAYS_SOFTWARE=1` before launching |
| Wheels don't move with sliders | Ensure joint_state_publisher_gui window is open and focused |
