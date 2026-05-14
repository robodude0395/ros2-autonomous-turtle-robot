# ROS 2 Autonomous TurtleBot

Autonomous navigation robot using ROS 2 Nav2 stack with SLAM. Built around an MD25 dual motor controller, Raspberry Pi Pico (micro-ROS firmware), and a Kinect 360 for perception.

## Architecture

```mermaid
graph TD
    subgraph Host["Host / Raspberry Pi (ROS 2 + Nav2)"]
        Nav2[Nav2]
        SLAM[SLAM]
        Kinect[Kinect Node]
        Agent[micro-ROS Agent]
    end

    subgraph Pico["Raspberry Pi Pico (micro-ROS firmware)"]
        Node[md25_base_controller]
    end

    subgraph Hardware["MD25 + EMG30 Motors"]
        MD25[MD25 Motor Controller]
    end

    Nav2 -->|cmd_vel| Agent
    SLAM -->|/map, /tf| Nav2
    Kinect -->|/depth, /rgb| SLAM

    Agent <-->|USB serial| Node

    Node -->|wheel_encoders| Agent
    Node -->|battery_voltage| Agent
    Node -->|motor_currents| Agent

    Node <-->|I2C GP0/GP1| MD25
```

## Repository Structure

```
firmware/          Pico micro-ROS firmware (C, Pico SDK)
  src/main.c       micro-ROS node with cmd_vel, encoders, diagnostics
  src/md25.c/.h    MD25 I2C driver
  CMakeLists.txt   Build configuration
  README.md        Firmware quickstart guide
```

## Quick Start

See [firmware/README.md](firmware/README.md) for build and flash instructions.
