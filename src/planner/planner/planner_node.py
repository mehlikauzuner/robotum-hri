import json

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
import math
from nav2_msgs.action import NavigateToPose


class PlannerNode(Node):

    def __init__(self):
        super().__init__("planner")

        self.get_logger().info("Planner Node Started.")

        self.subscription = self.create_subscription(
            String,
            "/semantic_command",
            self.command_callback,
            10
        )

        self.response_publisher = self.create_publisher(
            String,
            "/robot_response",
            10
        )

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose"
        )

        self.current_target = "the destination"
        self.navigation_active = False

        # Safe approach distance from semantic object
        self.safe_approach_distance = 0.40

        # Latest robot position in odom frame
        self.robot_x = None
        self.robot_y = None

        self.odom_subscription = self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10
        )

    def odom_callback(self, msg):
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y

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
            target = data.get("target", "the destination")

            # Ignore duplicate commands while navigation is active.
            if self.navigation_active:
                self.get_logger().info(
                    f"Ignoring duplicate navigation command for {target}."
                )
                return

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

            # Calculate a safe goal in front of the semantic object.
            goal_x, goal_y = self.calculate_safe_goal(x, y)

            self.send_navigation_goal(goal_x, goal_y, target)
            return

        # Unknown action
        self.get_logger().warn(
            f"Unknown action: {action}"
        )

    def publish_response(self, text):
        msg = String()
        msg.data = text
        self.response_publisher.publish(msg)

        self.get_logger().info(
            f"Robot response: {text}"
        )

    def calculate_safe_goal(self, target_x, target_y):
        if self.robot_x is None or self.robot_y is None:
            self.get_logger().warn(
                "Robot pose not available. Using semantic target directly."
            )
            return target_x, target_y

        dx = target_x - self.robot_x
        dy = target_y - self.robot_y
        distance = math.hypot(dx, dy)

        if distance <= self.safe_approach_distance:
            return self.robot_x, self.robot_y

        direction_x = dx / distance
        direction_y = dy / distance

        goal_x = target_x - direction_x * self.safe_approach_distance
        goal_y = target_y - direction_y * self.safe_approach_distance

        self.get_logger().info(
            f"Safe approach goal: "
            f"x={goal_x:.2f}, y={goal_y:.2f} "
            f"(object: x={target_x:.2f}, y={target_y:.2f})"
        )

        return goal_x, goal_y

    def send_navigation_goal(self, x, y, target):

        self.navigation_active = True
        self.current_target = target

        self.get_logger().info(
            f"Sending navigation goal: "
            f"x={x:.2f}, y={y:.2f}"
        )

        self.publish_response(
            f"I am going to {target}."
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
            self.navigation_active = False
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

        self.navigation_active = False

        self.get_logger().info(
            f"Navigation finished with status: "
            f"{result.status}"
        )

        self.get_logger().info(
            f"Result: {result.result}"
        )

        if result.status == 4:
            self.publish_response(
                f"I have arrived at {self.current_target}."
            )
        else:
            self.publish_response(
                f"I could not reach {self.current_target}."
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