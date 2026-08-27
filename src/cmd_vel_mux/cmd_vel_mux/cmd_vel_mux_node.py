import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped


class CmdVelMux(Node):

    def __init__(self):
        super().__init__('cmd_vel_mux')

        self.nav_sub = self.create_subscription(
            TwistStamped,
            '/cmd_vel_nav',
            self.nav_callback,
            10
        )

        self.llm_sub = self.create_subscription(
            TwistStamped,
            '/cmd_vel_llm',
            self.llm_callback,
            10
        )

        self.pub = self.create_publisher(
            TwistStamped,
            '/cmd_vel_muxed',
            10
        )

        self.get_logger().info('CmdVel Mux started')

    def nav_callback(self, msg):
        self.pub.publish(msg)

    def llm_callback(self, msg):
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = CmdVelMux()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
