import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray


class ObstacleMarkers(Node):

    def __init__(self):
        super().__init__('obstacle_markers')

        self.publisher = self.create_publisher(
            MarkerArray,
            '/obstacle_markers',
            10
        )

        self.semantic_map_path = (
            "/home/mehlika/robotum-hri-github/"
            "environments/test_environment/semantic_map.json"
        )

        self.objects = self.load_semantic_map()

        self.timer = self.create_timer(1.0, self.publish_markers)

    def load_semantic_map(self):
        try:
            import json

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

    def publish_markers(self):
        marker_array = MarkerArray()

        for i, (name, pos) in enumerate(self.objects.items()):

            marker = Marker()
            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'obstacles'
            marker.id = i
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD

            marker.pose.position.x = pos['x']
            marker.pose.position.y = pos['y']
            marker.pose.position.z = 0.2

            marker.pose.orientation.w = 1.0

            marker.scale.x = 0.25
            marker.scale.y = 0.25
            marker.scale.z = 0.25

            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 0.0
            marker.color.a = 1.0

            marker_array.markers.append(marker)

            text = Marker()
            text.header.frame_id = 'map'
            text.header.stamp = self.get_clock().now().to_msg()
            text.ns = 'obstacle_names'
            text.id = i
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD

            text.pose.position.x = pos['x']
            text.pose.position.y = pos['y']
            text.pose.position.z = 0.5
            text.pose.orientation.w = 1.0

            text.scale.z = 0.2

            text.color.r = 1.0
            text.color.g = 1.0
            text.color.b = 1.0
            text.color.a = 1.0

            text.text = name

            marker_array.markers.append(text)

        self.publisher.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleMarkers()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
