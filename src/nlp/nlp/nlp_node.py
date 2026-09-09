import json
import urllib.request
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class NLPNode:

    def __init__(self):
        self.node = None


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

        self.response_publisher = self.create_publisher(
            String,
            "/robot_response",
            10
        )

        # Stores the previous clarification context.
        # Example:
        # {"type": "navigate_target", "original_command": "Go there."}
        self.pending_context = None

        self.get_logger().info("NLP Node Started.")

    def command_callback(self, msg):
        command = msg.data.strip()

        self.get_logger().info(
            f"Received command: {command}"
        )

        threading.Thread(
            target=self.process_command,
            args=(command,),
            daemon=True
        ).start()

    def process_command(self, command):
        context_text = ""

        if self.pending_context is not None:
            context_text = (
                "PREVIOUS DIALOGUE CONTEXT: "
                "The previous user request required clarification. "
                "The user is now answering that clarification. "
                f"Previous user command: "
                f"{self.pending_context['original_command']} "
                "The previous assistant question was: "
                "\"Which target do you mean?\" "
                "Interpret the current user message as the answer "
                "to that question if possible. "
            )

            self.get_logger().info(
                "Using previous dialogue context."
            )

        prompt = (
            "Extract the user's action and target. Return JSON only. "
            "Navigation: "
            '{"status":"valid","action":"navigate","target":"TARGET"}. '
            "Forward: "
            '{"status":"valid","action":"move","direction":"forward"}. '
            "Backward: "
            '{"status":"valid","action":"move","direction":"backward"}. '
            "Left rotation: "
            '{"status":"valid","action":"rotate","direction":"left"}. '
            "Right rotation: "
            '{"status":"valid","action":"rotate","direction":"right"}. '
            "Stop: "
            '{"status":"valid","action":"stop"}. '
            "For navigation, extract the target exactly as stated. "
            "The target may be any person, object, place, or location. "
            "Do not check whether the target exists and never invent coordinates. "
            'If the target is unclear, return '
            '{"status":"clarification","response":"Which target do you mean?"}. '
            "If previous dialogue context exists, interpret the current message "
            "as the answer to the clarification. "
            f"{context_text}"
            f"USER: {command}"
        )

        payload = json.dumps({
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0
            }
        }).encode("utf-8")

        request = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        self.get_logger().info("Sending command to Ollama...")

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            parsed_command = result["response"].strip()

            self.get_logger().info(
                f"Ollama response: {parsed_command}"
            )

            # Check the returned status so that dialogue context
            # can be updated.
            try:
                parsed_data = json.loads(parsed_command)
                status = parsed_data.get("status")

                if status == "clarification":
                    self.pending_context = {
                        "type": "navigate_target",
                        "original_command": command
                    }

                    self.get_logger().info(
                        "Clarification context saved."
                    )

                elif status == "valid":
                    self.pending_context = None

                    self.get_logger().info(
                        "Dialogue context cleared after valid command."
                    )

            except json.JSONDecodeError:
                self.get_logger().warning(
                    "Ollama returned non-JSON output."
                )

            # Route the result according to its status.
            if status == "valid":
                output = String()
                output.data = parsed_command
                self.publisher.publish(output)

                self.get_logger().info(
                    f"Published to /parsed_command: {parsed_command}"
                )

            elif status in ("clarification", "invalid"):
                response = parsed_data.get("response", "")

                output = String()
                output.data = response
                self.response_publisher.publish(output)

                self.get_logger().info(
                    f"Published to /robot_response: {response}"
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
