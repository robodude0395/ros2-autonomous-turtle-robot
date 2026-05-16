"""
Differential drive odometry node.

Computes odometry from raw encoder ticks and publishes:
  - nav_msgs/Odometry on /odom
  - TF broadcast: odom → base_link

Subscribes:
    /wheel/left/encoder  (std_msgs/Int32)
    /wheel/right/encoder (std_msgs/Int32)

Uses a fixed-rate timer to sample both encoders simultaneously,
avoiding phantom rotations from unsynchronized left/right callbacks.
"""

import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster


def quaternion_from_yaw(yaw: float) -> Quaternion:
    """Create a Quaternion message from a yaw angle."""
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class DiffDriveOdom(Node):

    def __init__(self):
        super().__init__('diff_drive_odom')

        # Parameters — must match your physical robot
        self.declare_parameter('ticks_per_revolution', 360)
        self.declare_parameter('wheel_radius', 0.05)        # metres
        self.declare_parameter('wheel_separation', 0.38)     # metres (centre-to-centre)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('publish_rate', 10.0)         # Hz
        self.declare_parameter('tick_deadband', 2)            # ignore changes <= this many ticks

        self.ticks_per_rev = self.get_parameter('ticks_per_revolution').value
        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.publish_tf = self.get_parameter('publish_tf').value
        publish_rate = self.get_parameter('publish_rate').value
        self.tick_deadband = self.get_parameter('tick_deadband').value

        # Derived
        self.metres_per_tick = (2.0 * math.pi * self.wheel_radius) / self.ticks_per_rev

        # State
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.left_ticks = 0
        self.right_ticks = 0
        self.prev_left_ticks = None
        self.prev_right_ticks = None
        self.last_time = None
        self.left_received = False
        self.right_received = False

        # Subscribers — just store the latest value
        self.create_subscription(Int32, 'wheel/left/encoder', self._left_cb, 10)
        self.create_subscription(Int32, 'wheel/right/encoder', self._right_cb, 10)

        # Publisher
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)

        # TF broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)

        # Fixed-rate timer — samples both encoders together
        timer_period = 1.0 / publish_rate
        self.create_timer(timer_period, self._update_odom)

        self.get_logger().info(
            f'DiffDriveOdom started: wheel_radius={self.wheel_radius}m, '
            f'wheel_sep={self.wheel_separation}m, ticks/rev={self.ticks_per_rev}, '
            f'rate={publish_rate}Hz'
        )

    def _left_cb(self, msg: Int32):
        self.left_ticks = msg.data
        self.left_received = True

    def _right_cb(self, msg: Int32):
        self.right_ticks = msg.data
        self.right_received = True

    def _update_odom(self):
        # Wait until we've received at least one message from each encoder
        if not self.left_received or not self.right_received:
            return

        now = self.get_clock().now()

        # Initialize baseline on first run
        if self.prev_left_ticks is None:
            self.prev_left_ticks = self.left_ticks
            self.prev_right_ticks = self.right_ticks
            self.last_time = now
            return

        # Compute deltas (snapshot both at the same instant)
        left_ticks = self.left_ticks
        right_ticks = self.right_ticks

        delta_left = left_ticks - self.prev_left_ticks
        delta_right = right_ticks - self.prev_right_ticks

        # Deadband: ignore tiny fluctuations (encoder noise)
        if abs(delta_left) <= self.tick_deadband and abs(delta_right) <= self.tick_deadband:
            # Still publish odom at current pose (for TF continuity) but with zero velocity
            self._publish(now, 0.0, 0.0)
            return

        dl = delta_left * self.metres_per_tick
        dr = delta_right * self.metres_per_tick

        self.prev_left_ticks = left_ticks
        self.prev_right_ticks = right_ticks

        # Differential drive kinematics
        d_centre = (dl + dr) / 2.0
        d_theta = (dr - dl) / self.wheel_separation

        # Update pose
        self.x += d_centre * math.cos(self.theta + d_theta / 2.0)
        self.y += d_centre * math.sin(self.theta + d_theta / 2.0)
        self.theta += d_theta

        # Time delta for velocity
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        vx = d_centre / dt if dt > 0 else 0.0
        vth = d_theta / dt if dt > 0 else 0.0

        self._publish(now, vx, vth)

    def _publish(self, now, vx, vth):
        """Publish odometry message and TF."""
        # Publish Odometry message
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = quaternion_from_yaw(self.theta)

        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth

        self.odom_pub.publish(odom)

        # Broadcast TF: odom → base_link
        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = now.to_msg()
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation = quaternion_from_yaw(self.theta)
            self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = DiffDriveOdom()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
