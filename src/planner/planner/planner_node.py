import json

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


class PlannerNode(Node):

    def __init__(self):
        super().__init__("planner")

        self.get_logger().info("Planner Node Started.")

        self.subscription = self.create_subscription(
            String,
            "/parsed_command",
            self.command_callback,
            10
        )

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose"
        )

    def command_callback(self, msg):
        command = msg.data.strip()

        self.get_logger().info(
            f"Command: {command}"
        )

        # JSON command parsing
        try:
            data = json.loads(command)
        except json.JSONDecodeError:
            self.get_logger().warn(
                "Invalid JSON command."
            )
            return

        action = data.get("action")

        # Navigate action
        if action == "navigate":

            x = data.get("x")
            y = data.get("y")

            if x is None or y is None:
                self.get_logger().warn(
                    "Navigate command requires x and y."
                )
                return

            try:
                x = float(x)
                y = float(y)
            except (TypeError, ValueError):
                self.get_logger().warn(
                    "x and y must be numeric values."
                )
                return

            self.send_navigation_goal(x, y)
            return

        # Unknown action
        self.get_logger().warn(
            f"Unknown action: {action}"
        )

    def send_navigation_goal(self, x, y):

        self.get_logger().info(
            f"Sending navigation goal: "
            f"x={x:.2f}, y={y:.2f}"
        )

        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error(
                "NavigateToPose action server is not available."
            )
            return

        goal_msg = NavigateToPose.Goal()

        goal_msg.pose = PoseStamped()

        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = (
            self.get_clock().now().to_msg()
        )

        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0

        goal_msg.pose.pose.orientation.z = 0.0
        goal_msg.pose.pose.orientation.w = 1.0

        future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(
                "Navigation goal was REJECTED."
            )
            return

        self.get_logger().info(
            "Navigation goal was ACCEPTED."
        )

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            self.get_result_callback
        )

    def get_result_callback(self, future):
        result = future.result()

        self.get_logger().info(
            f"Navigation finished with status: "
            f"{result.status}"
        )

        self.get_logger().info(
            f"Result: {result.result}"
        )

    def feedback_callback(self, feedback_msg):

        feedback = feedback_msg.feedback

        self.get_logger().info(
            f"Distance remaining: "
            f"{feedback.distance_remaining:.2f} m"
        )


def main(args=None):

    rclpy.init(args=args)

    node = PlannerNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()