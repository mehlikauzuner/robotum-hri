import json

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import String
from geometry_msgs.msg import PointStamped
import tf2_ros
import tf2_geometry_msgs
from environment_manager_interfaces.srv import AddSemanticObject


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

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(
            self.tf_buffer,
            self
        )

        self.clicked_point_subscription = self.create_subscription(
            PointStamped,
            "/clicked_point",
            self.clicked_point_callback,
            10
        )

        self.last_clicked_point_map = None
        self.clicked_point_map_publisher = self.create_publisher(
            PointStamped,
            "/semantic_clicked_point",
            10
        )

        self.publisher = self.create_publisher(
            String,
            "/semantic_command",
            10
        )

        self.add_object_service = self.create_service(
            AddSemanticObject,
            "/add_semantic_object",
            self.add_object_callback
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

    def clicked_point_callback(self, msg):
        try:
            msg.header.stamp.sec = 0
            msg.header.stamp.nanosec = 0

            point_in_map = self.tf_buffer.transform(
                msg,
                "map",
                timeout=Duration(seconds=1.0)
            )

            self.last_clicked_point_map = point_in_map
            point_in_map.header.frame_id = "map"
            self.clicked_point_map_publisher.publish(point_in_map)

            self.get_logger().info(
                "Clicked point transformed to map: "
                f"x={point_in_map.point.x:.3f}, "
                f"y={point_in_map.point.y:.3f}"
            )

        except tf2_ros.TransformException as e:
            self.get_logger().warning(
                f"Could not transform clicked point to map: {e}"
            )

    def add_object_callback(self, request, response):
        try:
            with open(self.semantic_map_path, "r") as f:
                data = json.load(f)

            objects = data.setdefault("objects", [])

            # Update existing object if the name already exists.
            existing = next(
                (
                    obj for obj in objects
                    if obj.get("name", "").lower() == request.name.lower()
                ),
                None
            )

            if existing:
                existing["name"] = request.name
                existing["type"] = request.type
                existing["x"] = self.last_clicked_point_map.point.x
                existing["y"] = self.last_clicked_point_map.point.y
            else:
                objects.append({
                    "name": request.name,
                    "type": request.type,
                    "x": self.last_clicked_point_map.point.x,
                    "y": self.last_clicked_point_map.point.y
                })

            with open(self.semantic_map_path, "w") as f:
                json.dump(data, f, indent=2)

            self.objects[request.name] = {
                "x": self.last_clicked_point_map.point.x,
                "y": self.last_clicked_point_map.point.y
            }

            response.success = True
            response.message = f'Object "{request.name}" saved.'

            self.get_logger().info(
                f'Object saved: {request.name} '
                f'({self.last_clicked_point_map.point.x}, {self.last_clicked_point_map.point.y})'
            )

        except (OSError, json.JSONDecodeError) as e:
            response.success = False
            response.message = f"Failed to save object: {e}"

            self.get_logger().error(
                f"Failed to save semantic object: {e}"
            )

        return response

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
