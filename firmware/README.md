# MD25 micro-ROS Firmware (Raspberry Pi Pico)

Differential drive base controller running on an RP2040. Communicates with the MD25 motor controller over I2C and exposes standard ROS 2 topics via micro-ROS over USB serial.

## Topics

| Topic | Type | Direction | Description |
|-------|------|-----------|-------------|
| `cmd_vel` | `geometry_msgs/Twist` | Subscribe | `linear.x` (m/s) + `angular.z` (rad/s) |
| `wheel/left/encoder` | `std_msgs/Int32` | Publish @ 10 Hz | Left wheel encoder ticks |
| `wheel/right/encoder` | `std_msgs/Int32` | Publish @ 10 Hz | Right wheel encoder ticks |
| `battery/voltage` | `std_msgs/Float32` | Publish @ 10 Hz | Battery voltage in volts |
| `wheel/left/current` | `std_msgs/Float32` | Publish @ 10 Hz | Left motor current in amps |
| `wheel/right/current` | `std_msgs/Float32` | Publish @ 10 Hz | Right motor current in amps |

A software watchdog stops the motors if no `cmd_vel` is received within 500 ms.

## Wiring

```
Pico GP0 (SDA) ──► Level Shifter LV ──► HV ──► MD25 SDA
Pico GP1 (SCL) ──► Level Shifter LV ──► HV ──► MD25 SCL
Pico 3V3        ──► Level Shifter LV ref
MD25 5V out     ──► Level Shifter HV ref
Common GND between Pico, level shifter, and MD25
MD25 powered by 12V battery
```

## Prerequisites

- Pico SDK 2.2.0 (installed via the VS Code Pico extension or manually)
- `arm-none-eabi-gcc` toolchain
- micro-ROS agent on the host machine

## Build

```bash
cd firmware

# Set to your ROS 2 distro (humble, iron, jazzy, kilted)
export ROS_DISTRO=humble

# Pull in the micro-ROS precompiled library and USB transport
git clone https://github.com/micro-ROS/micro_ros_raspberrypi_pico_sdk --branch $ROS_DISTRO microros_sdk
cp -r microros_sdk/libmicroros .
cp microros_sdk/pico_uart_transport.c .
cp microros_sdk/pico_uart_transports.h .
rm -rf microros_sdk   # no longer needed

mkdir build && cd build
cmake ..
make -j$(nproc)
```

## Flash

Hold BOOTSEL on the Pico, plug USB, then:

```bash
cp md25_microros.uf2 /Volumes/RPI-RP2   # macOS
# or
cp md25_microros.uf2 /media/$USER/RPI-RP2  # Linux
```

## Run the micro-ROS Agent

The agent must be built from source to ensure DDS type compatibility with your ROS 2 install.

### Build the agent (one-time setup on the RPi)

```bash
sudo apt install -y g++ cmake python3-rosdep python3-colcon-common-extensions
sudo rosdep init
rosdep update

source /opt/ros/$ROS_DISTRO/setup.bash
mkdir -p ~/microros_ws/src
cd ~/microros_ws/src
git clone -b $ROS_DISTRO https://github.com/micro-ROS/micro-ROS-Agent.git
git clone -b $ROS_DISTRO https://github.com/micro-ROS/micro_ros_msgs.git
cd ~/microros_ws
rosdep install --from-paths src --ignore-src -y
colcon build
```

Add to your `~/.bashrc` so it's always available:

```bash
echo "source ~/microros_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### Start the agent

```bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200
```

## Verify

```bash
ros2 topic list
ros2 topic echo /wheel/left/encoder
ros2 topic echo /wheel/right/encoder
ros2 topic echo /battery/voltage
ros2 topic echo /wheel/left/current
ros2 topic echo /wheel/right/current
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.3}, angular: {z: 0.0}}"
```

## Tuning

These values **must** be measured and set for your specific robot before use with Nav2.

Edit `src/main.c`:

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `WHEEL_SEPARATION` | 0.235 | m | Centre-to-centre distance between the two wheels. Measure with a ruler. |
| `MAX_LINEAR_VEL` | 1.0 | m/s | Top speed of the robot at full motor power. The EMG30 is ~1.0 m/s unloaded at 12V — measure under load for accuracy. |
| `CMD_VEL_TIMEOUT_MS` | 500 | ms | Motors stop if no `cmd_vel` received within this window. Lower = safer, higher = tolerates network jitter. |
| `PUBLISH_PERIOD_MS` | 100 | ms | How often encoder/battery/current data is published (100 ms = 10 Hz). |

Edit `src/md25.h`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MD25_SDA_PIN` | 0 | I2C SDA GPIO pin |
| `MD25_SCL_PIN` | 1 | I2C SCL GPIO pin |
| `MD25_ADDR` | 0x58 | MD25 7-bit I2C address (0xB0 >> 1). Change if you moved the address jumper. |
| `MD25_I2C_FREQ` | 100000 | I2C clock speed in Hz. MD25 supports up to 100 kHz. |

## How to Measure

**Wheel separation:** Place the robot on a flat surface. Measure the distance between the centre of the left tyre contact patch and the centre of the right tyre contact patch.

**Max linear velocity:** Mark a 1 m distance on the floor. Send full-speed `cmd_vel` and time how long the robot takes to cross it. `MAX_LINEAR_VEL = 1.0 / time_seconds`.

**Encoder ticks per revolution:** The EMG30 has 360 ticks/rev of the output shaft. If you're using different motors, check their datasheet and update odometry calculations accordingly.

**MD25 I2C address:** Power the MD25 with no I2C commands sent. The green LED will flash the address: one long flash + N short flashes (N=0 means 0xB0, N=1 means 0xB2, etc.).
