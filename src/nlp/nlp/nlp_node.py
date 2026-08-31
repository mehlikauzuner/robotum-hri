import json
import urllib.request

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class NLPNode(Node):

    def __init__(self):
        super().__init__("nlp_node")

        self.subscription = self.create_subscription(
            String,
            "/user_command",
            self.command_callback,
            10
        )

        self.publisher = self.create_publisher(
            String,
            "/parsed_command",
            10
        )

        self.get_logger().info("NLP Node Started.")

    def command_callback(self, msg):
        command = msg.data.strip()

        self.get_logger().info(
            f"Received command: {command}"
        )

        prompt = (
            "You are a robot command parser. "
            "Convert the user command into ONLY one valid JSON object. "
            "Allowed formats: "
            '{"action":"move","direction":"forward|backward"}, '
            '{"action":"rotate","direction":"left|right"}, '
            '{"action":"stop"}, '
            '{"action":"navigate","x":number,"y":number}, '
'{"action":"navigate","target":"home|tree|car|Eren|Mehlika|school|hospital|market|park"}. '
            f"User command: {command}. "
            "Return JSON only, no markdown, no explanation."
        )

        payload = json.dumps({
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "format": "json",
            "stream": False
        }).encode("utf-8")

        request = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        self.get_logger().info("Sending command to Ollama...")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            parsed_command = result["response"].strip()

            self.get_logger().info(
                f"Ollama response: {parsed_command}"
            )

            # Publish parsed JSON command for the planner
            output = String()
            output.data = parsed_command
            self.publisher.publish(output)

            self.get_logger().info(
                f"Published to /parsed_command: {parsed_command}"
            )

        except Exception as e:
            self.get_logger().error(
                f"Ollama request failed: {e}"
            )


def main(args=None):
    rclpy.init(args=args)

    node = NLPNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

