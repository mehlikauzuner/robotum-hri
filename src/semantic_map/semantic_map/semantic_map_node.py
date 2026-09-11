import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SemanticMapNode(Node):

    def __init__(self):
        super().__init__("semantic_map")

        self.semantic_map_path = (
            "/home/mehlika/robotum-hri-github/"
            "environments/test_environment/semantic_map.json"
        )

        self.objects = self.load_semantic_map()

        self.subscription = self.create_subscription(
            String,
            "/parsed_command",
            self.command_callback,
            10
        )

        self.publisher = self.create_publisher(
            String,
            "/semantic_command",
            10
        )

        self.get_logger().info("Semantic Map Node Started.")

    def load_semantic_map(self):
        try:
            with open(self.semantic_map_path, "r") as f:
                data = json.load(f)

            objects = {}

            for obj in data.get("objects", []):
                name = obj.get("name")

                if not name:
                    continue

                objects[name] = {
                    "x": obj["x"],
                    "y": obj["y"]
                }

            self.get_logger().info(
                f"Loaded {len(objects)} semantic objects."
            )

            return objects

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            self.get_logger().error(
                f"Failed to load semantic map: {e}"
            )
            return {}

    def command_callback(self, msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warning("Invalid JSON command.")
            return

        # Direct movement/rotation commands
        # These are passed through without changing the existing
        # navigation behavior.
        if data.get("action") in ["move", "rotate"]:
            output = String()
            output.data = msg.data
            self.publisher.publish(output)

            self.get_logger().info(
                f"Direct command -> {msg.data}"
            )
            return

        # Existing navigation logic
        target = data.get("target")

        if target is None:
            return

        target_key = next(
            (name for name in self.objects if name.lower() == target.lower()),
            None
        )

        if target_key is None:
            self.get_logger().warning(f"Unknown target: {target}")
            return

        obj = self.objects[target_key]

        output = String()
        output.data = json.dumps({
            "action": "navigate",
            "target": target,
            "x": obj["x"],
            "y": obj["y"]
        })

        self.publisher.publish(output)

        self.get_logger().info(
            f"{target} -> x={obj['x']}, y={obj['y']}"
        )


def main(args=None):
    rclpy.init(args=args)

    node = SemanticMapNode()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
