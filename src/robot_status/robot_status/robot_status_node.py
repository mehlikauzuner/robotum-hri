import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class RobotStatusNode(Node):
    def __init__(self):
        super().__init__("robot_status")

        self.status_publisher = self.create_publisher(
            String,
            "/robot_status",
            10,
        )

        self.response_subscription = self.create_subscription(
            String,
            "/robot_response",
            self.response_callback,
            10,
        )

        self.get_logger().info("Robot Status Node started.")

    def response_callback(self, msg):
        response = msg.data.strip()

        if not response:
            return

        status = {
            "current_action": response,
            "queue": [],
            "error": "",
        }

        if response.lower().startswith("i could not reach"):
            status["error"] = response

        status_msg = String()
        status_msg.data = json.dumps(status, separators=(",", ":"))

        self.status_publisher.publish(status_msg)

        self.get_logger().info(
            f"Published robot status: {status_msg.data}"
        )


def main(args=None):
    rclpy.init(args=args)

    node = RobotStatusNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
