import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SemanticMapNode(Node):

    def __init__(self):
        super().__init__("semantic_map")

        self.objects = {
            "home": {"x": 0.928, "y": 1.561},
            "tree": {"x": 2.017, "y": 1.556},
            "car": {"x": 3.099, "y": 1.550},
            "Eren": {"x": 0.933, "y": 0.521},
            "Mehlika": {"x": 2.029, "y": 0.512},
            "school": {"x": 3.127, "y": 0.514},
            "hospital": {"x": 0.928, "y": -0.533},
            "market": {"x": 2.022, "y": -0.535},
            "park": {"x": 3.093, "y": -0.523},
        }

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

    def command_callback(self, msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warning("Invalid JSON command.")
            return

        target = data.get("target")

        if target is None:
            return

        if target not in self.objects:
            self.get_logger().warning(f"Unknown target: {target}")
            return

        obj = self.objects[target]

        output = String()
        output.data = json.dumps({
            "action": "navigate",
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
