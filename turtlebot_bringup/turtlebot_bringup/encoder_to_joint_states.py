"""
Converts raw encoder tick counts from the MD25/EMG30 motors into
sensor_msgs/JointState messages for robot_state_publisher.

Subscribes:
    /wheel/left/encoder  (std_msgs/Int32)  — cumulative encoder ticks
    /wheel/right/encoder (std_msgs/Int32)  — cumulative encoder ticks

Publishes:
    /joint_states (sensor_msgs/JointState) — wheel joint positions in radians
"""

import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from sensor_msgs.msg import JointState


class EncoderToJointStates(Node):

    def __init__(self):
        super().__init__('encoder_to_joint_states')

        # EMG30 encoder: 360 ticks per revolution of the output shaft
        self.declare_parameter('ticks_per_revolution', 360)
        self.ticks_per_rev = self.get_parameter('ticks_per_revolution').value

        # Joint names must match the URDF joint names
        self.declare_parameter('left_joint_name', 'left_wheel_joint')
        self.declare_parameter('right_joint_name', 'right_wheel_joint')
        self.left_joint = self.get_parameter('left_joint_name').value
        self.right_joint = self.get_parameter('right_joint_name').value

        # State
        self.left_ticks = 0
        self.right_ticks = 0
        self.left_prev_ticks = None
        self.right_prev_ticks = None

        # Subscribers
        self.create_subscription(Int32, 'wheel/left/encoder', self._left_cb, 10)
        self.create_subscription(Int32, 'wheel/right/encoder', self._right_cb, 10)

        # Publisher
        self.joint_pub = self.create_publisher(JointState, 'joint_states', 10)

        self.get_logger().info(
            f'Encoder→JointState node started '
            f'(ticks/rev={self.ticks_per_rev}, '
            f'joints=[{self.left_joint}, {self.right_joint}])'
        )

    def _left_cb(self, msg: Int32):
        self.left_ticks = msg.data
        self._publish_joint_states()

    def _right_cb(self, msg: Int32):
        self.right_ticks = msg.data
        self._publish_joint_states()

    def _ticks_to_radians(self, ticks: int) -> float:
        """Convert encoder ticks to radians."""
        return (ticks / self.ticks_per_rev) * 2.0 * math.pi

    def _publish_joint_states(self):
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = [self.left_joint, self.right_joint]
        js.position = [
            self._ticks_to_radians(self.left_ticks),
            self._ticks_to_radians(self.right_ticks),
        ]
        # Velocity and effort left empty — not needed for visualization
        self.joint_pub.publish(js)


def main(args=None):
    rclpy.init(args=args)
    node = EncoderToJointStates()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
