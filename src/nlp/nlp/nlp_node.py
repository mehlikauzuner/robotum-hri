import json
import urllib.request
import threading

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

        self.response_publisher = self.create_publisher(
            String,
            "/robot_response",
            10
        )

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

    def publish_parsed(self, parsed_data):
        output = String()
        output.data = json.dumps(parsed_data)

        self.publisher.publish(output)

        self.get_logger().info(
            f"Published to /parsed_command: {output.data}"
        )

    def publish_response(self, response):
        output = String()
        output.data = response

        self.response_publisher.publish(output)

        self.get_logger().info(
            f"Published to /robot_response: {response}"
        )

    def deterministic_parse(self, command):
        """
        Handle common Robotum commands without Ollama.

        Returns a parsed command dictionary when the command
        is unambiguous. Returns None when Ollama is required.
        """

        text = command.strip()
        normalized = text.lower()

        # STOP
        if normalized in {
            "stop",
            "halt",
            "dur",
            "dur robot",
            "stop robot",
        }:
            return {
                "status": "valid",
                "action": "stop",
            }

        # FORWARD
        if normalized in {
            "forward",
            "move forward",
            "go forward",
            "ileri",
            "ileri git",
        }:
            return {
                "status": "valid",
                "action": "move",
                "direction": "forward",
            }

        # BACKWARD
        if normalized in {
            "backward",
            "move backward",
            "go backward",
            "geri",
            "geri git",
        }:
            return {
                "status": "valid",
                "action": "move",
                "direction": "backward",
            }

        # LEFT
        if normalized in {
            "left",
            "turn left",
            "rotate left",
            "sol",
            "sola dön",
        }:
            return {
                "status": "valid",
                "action": "rotate",
                "direction": "left",
            }

        # RIGHT
        if normalized in {
            "right",
            "turn right",
            "rotate right",
            "sağ",
            "sağa dön",
        }:
            return {
                "status": "valid",
                "action": "rotate",
                "direction": "right",
            }

        # NAVIGATION
        navigation_prefixes = (
            "go to ",
            "move to ",
            "navigate to ",
            "drive to ",
            "take me to ",
            "git ",
            "git to ",
        )

        for prefix in navigation_prefixes:
            if normalized.startswith(prefix):
                target = text[len(prefix):].strip()

                if target:
                    return {
                        "status": "valid",
                        "action": "navigate",
                        "target": target,
                    }

        return None

    def process_command(self, command):

        # First handle deterministic commands locally.
        deterministic_result = self.deterministic_parse(command)

        if deterministic_result is not None:
            self.get_logger().info(
                "Command handled locally. Ollama not required."
            )

            self.pending_context = None
            self.publish_parsed(deterministic_result)
            return

        # Only commands that cannot be parsed locally
        # are sent to Ollama.
        context_text = ""

        if self.pending_context is not None:
            context_text = (
              "PREVIOUS DIALOGUE CONTEXT: "
              f'The previous user command was: "{self.pending_context["original_command"]}". '
              'The assistant asked: "Which target do you mean?". '
              "The user is now answering that question. "
              "Treat the current user message as the target they selected. "
              "Extract the target from the current user message. "
              "Do not ask for clarification again. "
              "Return a valid navigation command using that target. "
            )

            self.get_logger().info(
                "Using previous dialogue context."
            )

        prompt = (
            "Parse the user's command. Return JSON only. "
            "For navigation return "
            '{"status":"valid","action":"navigate","target":"TARGET"}. '
            "For forward return "
            '{"status":"valid","action":"move","direction":"forward"}. '
            "For backward return "
            '{"status":"valid","action":"move","direction":"backward"}. '
            "For left rotation return "
            '{"status":"valid","action":"rotate","direction":"left"}. '
            "For right rotation return "
            '{"status":"valid","action":"rotate","direction":"right"}. '
            "For stop return "
            '{"status":"valid","action":"stop"}. '
            "For navigation, copy the target exactly. "
            "Never generate coordinates. "
            'If the target is unclear, return '
            '{"status":"clarification","response":"Which target do you mean?"}. '
            f"USER: {command} "
            f"{context_text}"
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

        self.get_logger().info(
            "Sending ambiguous command to Ollama..."
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

            parsed_command = result["response"].strip()

            self.get_logger().info(
                f"Ollama response: {parsed_command}"
            )

            try:
                parsed_data = json.loads(parsed_command)
            except json.JSONDecodeError:
                self.get_logger().error(
                    "Ollama returned non-JSON output."
                )
                return

            status = parsed_data.get(
                "status",
                "invalid"
            )

            if status == "clarification":

                self.pending_context = {
                    "type": "navigate_target",
                    "original_command": command,
                }

                self.get_logger().info(
                    "Clarification context saved."
                )

                self.publish_response(
                    parsed_data.get(
                        "response",
                        "Which target do you mean?",
                    )
                )

            elif status == "valid":

                self.pending_context = None

                self.get_logger().info(
                    "Dialogue context cleared after valid command."
                )

                self.publish_parsed(parsed_data)

            else:

                self.publish_response(
                    parsed_data.get(
                        "response",
                        "I could not understand the command.",
                    )
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
