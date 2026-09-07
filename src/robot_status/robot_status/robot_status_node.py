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

        self.status_event_subscription = self.create_subscription(
            String,
            "/robot_status_event",
            self.status_event_callback,
            10,
        )

        self.current_action = "Idle"
        self.status = "idle"
        self.error = ""

        self.get_logger().info("Robot Status Node started.")

    def response_callback(self, msg):
        response = msg.data.strip()

        if not response:
            return

        self.current_action = response

        if response.lower().startswith("i could not reach"):
            self.error = response

        self.publish_status()

    def status_event_callback(self, msg):
        try:
            event = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warning(
                "Invalid robot status event."
            )
            return

        if isinstance(event.get("current_action"), str):
            self.current_action = event["current_action"]

        if isinstance(event.get("status"), str):
            self.status = event["status"]

        if isinstance(event.get("error"), str):
            self.error = event["error"]

        self.publish_status()

    def publish_status(self):
        status = {
            "current_action": self.current_action,
            "status": self.status,
            "queue": [],
            "error": self.error,
        }

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
