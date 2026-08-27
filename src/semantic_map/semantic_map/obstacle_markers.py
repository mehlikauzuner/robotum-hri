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

        self.objects = {
            "engel_1": {"x": 0.928, "y": 1.561},
            "engel_2": {"x": 2.017, "y": 1.556},
            "engel_3": {"x": 3.099, "y": 1.550},
            "engel_4": {"x": 0.933, "y": 0.521},
            "engel_5": {"x": 2.029, "y": 0.512},
            "engel_6": {"x": 3.127, "y": 0.514},
            "engel_7": {"x": 0.928, "y": -0.533},
            "engel_8": {"x": 2.022, "y": -0.535},
            "engel_9": {"x": 3.093, "y": -0.523},
        }

        self.timer = self.create_timer(1.0, self.publish_markers)

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
