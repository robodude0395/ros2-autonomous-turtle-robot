# Ubuntu VM + Cyclone DDS Setup Guide

How to run a full ROS 2 desktop environment (RViz, Nav2, SLAM) on an M-series Mac and connect it to a Raspberry Pi over the local network.

## Architecture

| Machine | Role |
|---------|------|
| **Raspberry Pi** | micro-ROS agent, hardware drivers, sensor publishers |
| **Ubuntu VM (on Mac)** | RViz, Nav2, SLAM, URDF visualization, development |
| **Mac host** | Code editing, Git, agentic coding tools |

## 1. Create the Ubuntu VM

### Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- [UTM](https://mac.getutm.app) (free) or Parallels (paid)
- Ubuntu 24.04 (Noble) ARM64 ISO

### Steps

1. Download and install UTM
2. Download the Ubuntu 24.04 ARM64 desktop ISO from [ubuntu.com](https://ubuntu.com/download/desktop)
3. In UTM, create a new VM:
   - **Type:** Virtualize (not Emulate)
   - **OS:** Linux
   - **CPU:** 4+ cores
   - **RAM:** 8 GB+
   - **Disk:** 64 GB+
   - **Network:** Shared (we'll change this later)
4. Mount the ISO and install Ubuntu
5. After install, remove the ISO from the VM's CD drive and reboot

## 2. Switch to Bridged Networking

The VM must be on the same subnet as the Raspberry Pi for ROS 2 discovery to work.

1. **Shut down** the VM (full shutdown, not suspend)
2. In UTM, select the VM → **Edit** → **Network**
3. Change mode from **Shared** to **Bridged**
4. Select your Mac's Wi-Fi adapter (`en0`) as the bridged interface
5. Boot the VM

### Verify

In the VM:
```bash
hostname -I
```

On the Pi:
```bash
ping <vm_ip>
```

Both should be on the same subnet (e.g., `192.168.1.x`). If the ping works, you're good.

## 3. Install ROS 2 Kilted in the VM

```bash
# Locale
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# ROS 2 apt repository
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/ros2.list

# Install ROS 2 desktop + Nav2 + SLAM
sudo apt update
sudo apt install -y ros-kilted-desktop ros-kilted-navigation2 ros-kilted-nav2-bringup ros-kilted-slam-toolbox

# Source ROS 2
echo "source /opt/ros/kilted/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 4. Install Cyclone DDS

On **both** the VM and the Pi:

```bash
sudo apt install -y ros-kilted-rmw-cyclonedds-cpp
```

## 5. Configure Cyclone DDS for Unicast Discovery

Multicast is unreliable over Wi-Fi. Use unicast peers instead.

### On the VM

Create `~/cyclonedds.xml`:

```xml
<CycloneDDS>
  <Domain>
    <General>
      <AllowMulticast>false</AllowMulticast>
    </General>
    <Discovery>
      <Peers>
        <Peer address="RASPBERRY_PI_IP"/>
        <Peer address="localhost"/>
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

### On the Pi

Create `~/cyclonedds.xml`:

```xml
<CycloneDDS>
  <Domain>
    <General>
      <AllowMulticast>false</AllowMulticast>
    </General>
    <Discovery>
      <Peers>
        <Peer address="VM_IP"/>
        <Peer address="localhost"/>
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

**Important:** The `localhost` peer is required on both machines. Without it, nodes running on the same machine cannot discover each other when multicast is disabled (e.g., the Kinect driver won't be visible to `depthimage_to_laserscan` on the Pi).

### Set environment variables (both machines)

Add to `~/.bashrc`:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/cyclonedds.xml
```

Then: `source ~/.bashrc`

## 6. Test the Connection

On the Pi:
```bash
ros2 topic pub /test std_msgs/msg/String "data: hello from pi" --once
```

On the VM:
```bash
ros2 topic echo /test
```

If the message appears, the full pipeline is working.

## 7. Verify RViz

In the VM:
```bash
rviz2
```

If it crashes or shows a black viewport, force software rendering:
```bash
export LIBGL_ALWAYS_SOFTWARE=1
rviz2
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `librmw_cyclonedds_cpp.so: cannot open shared object` | Install the package: `sudo apt install ros-kilted-rmw-cyclonedds-cpp` |
| VM and Pi can't ping each other | Switch VM network to Bridged mode (see step 2) |
| `ros2 topic list` doesn't show topics from the other machine | Check both machines have matching `cyclonedds.xml` with correct IPs, `localhost` in peers, and `RMW_IMPLEMENTATION` is set |
| Nodes on the same machine can't see each other | Add `<Peer address="localhost"/>` to `cyclonedds.xml` |
| RViz black screen / crash | Set `export LIBGL_ALWAYS_SOFTWARE=1` before launching |
| VM gets IP on wrong subnet (e.g., `192.168.64.x`) | VM is still on Shared/NAT networking — switch to Bridged |

## Notes

- If your router assigns dynamic IPs, the addresses in `cyclonedds.xml` may need updating after a reboot. Consider setting static IPs or using mDNS hostnames (e.g., `pi.local`).
- UTM supports shared folders between Mac and VM — useful for editing code on the Mac and building in the VM.
- Both machines must use the same `ROS_DOMAIN_ID` (defaults to 0 if unset).
