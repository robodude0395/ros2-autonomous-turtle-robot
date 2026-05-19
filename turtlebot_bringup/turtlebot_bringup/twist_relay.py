"""
Relay node: subscribes to TwistStamped and republishes as Twist.

Nav2 Kilted defaults to publishing geometry_msgs/msg/TwistStamped on cmd_vel,
but micro-ROS firmware expects geometry_msgs/msg/Twist. This node bridges the gap.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped


class TwistRelay(Node):
    def __init__(self):
        super().__init__('twist_relay')

        self.declare_parameter('input_topic', '/cmd_vel_stamped')
        self.declare_parameter('output_topic', '/cmd_vel')

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value

        self.pub = self.create_publisher(Twist, output_topic, 10)
        self.sub = self.create_subscription(
            TwistStamped, input_topic, self._callback, 10
        )

        self.get_logger().info(
            f'Relaying TwistStamped [{input_topic}] → Twist [{output_topic}]'
        )

    def _callback(self, msg: TwistStamped):
        twist = Twist()
        twist.linear = msg.twist.linear
        twist.angular = msg.twist.angular
        self.pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = TwistRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
