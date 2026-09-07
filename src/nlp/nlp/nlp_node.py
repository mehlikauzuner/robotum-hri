import json
import urllib.request

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
            "You are the NLP and dialogue system of a mobile robot. "
            "Your task is to understand the user's intention and return "
            "ONLY ONE valid JSON object. "

            "AVAILABLE NAVIGATION TARGETS: "
            "home, tree, car, Eren, Mehlika, school, hospital, market, park. "

            "There are THREE possible statuses: valid, invalid, clarification. "

            "IMPORTANT DECISION RULES: "

            "1. VALID: "
            "Use valid when the user clearly specifies an available target "
            "or a supported robot action. "

            "Examples: "
            "'Go to hospital' -> "
            '{"status":"valid","action":"navigate","target":"hospital"}. '
            "'Go to the park' -> "
            '{"status":"valid","action":"navigate","target":"park"}. '
            "'Move forward' -> "
            '{"status":"valid","action":"move","direction":"forward"}. '
            "'Turn left' -> "
            '{"status":"valid","action":"rotate","direction":"left"}. '
            "'Stop' -> "
            '{"status":"valid","action":"stop"}. '

            "2. INVALID: "
            "Use invalid ONLY when the user clearly specifies a particular "
            "destination or action, but that destination or action is not "
            "available or supported. "

            "Examples: "
            "'Go to airport' -> "
            '{"status":"invalid","response":"I cannot go to the airport because it is not available on my map."}. '
            "'Go to the airport' -> invalid. "
            "'Go to the beach' -> invalid. "

            "3. CLARIFICATION: "
            "Use clarification when the user's intended target or action "
            "is NOT clear enough to determine what they want. "
            "Generic words are NOT target names. "
            "Words such as obstacle, place, destination, location, "
            "there, somewhere, or here do NOT identify a specific target. "

            "Examples: "
            "'Go to the obstacle' -> clarification. "
            "'Go there' -> clarification. "
            "'Go to the place' -> clarification. "
            "'Take me there' -> clarification. "
            "'Go somewhere' -> clarification. "

            "For clarification, ask the user which target they mean. "
            "Example response: "
            '{"status":"clarification","response":"Which target do you mean?"}. '

            "VERY IMPORTANT: "
            "The word 'obstacle' is NOT an unavailable destination. "
            "It is a generic description and therefore MUST produce "
            "clarification, NOT invalid. "

            "CONTEXT RULE: "
            "When previous dialogue context contains a clarification "
            "question asking which target the user means, the CURRENT "
            "user message is the answer to that question. "

            "If the answer is one of the available navigation targets, "
            "return valid navigation to that target. "

            "If the answer is a specific destination name but it is NOT "
            "one of the available navigation targets, return invalid. "
            "Do NOT ask for clarification again. "

            "If the answer is generic or non-specific, such as "
            "there, somewhere, place, location, destination, or obstacle, "
            "return clarification. "

            "IMPORTANT: 'party' is a specific destination name. "
            "Since 'party' is not an available navigation target, "
            "return invalid, NOT clarification. "

            "For example: "
            "Previous request: 'Go there.' "
            "Assistant: 'Which target do you mean?' "
            "User: 'tree' "
            "-> "
            '{"status":"valid","action":"navigate","target":"tree"}. '

            "For valid navigation use: "
            '{"status":"valid","action":"navigate","target":"TARGET"}. '

            "For valid movement use: "
            '{"status":"valid","action":"move","direction":"forward|backward"}, '
            '{"status":"valid","action":"rotate","direction":"left|right"}, '
            '{"status":"valid","action":"stop"}. '

            "For invalid requests use: "
            '{"status":"invalid","response":"short explanation to the user"}. '

            "For ambiguous requests use: "
            '{"status":"clarification","response":"short question asking the user for clarification"}. '

            "Never invent a target. "
            "Never invent coordinates. "
            "Return JSON only. "
            "Do not return markdown or explanations outside the JSON. "

            f"{context_text}"
            f"CURRENT USER COMMAND: {command}"
        )

        self.get_logger().info(
            f"Prompt length: {len(prompt)} characters"
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
