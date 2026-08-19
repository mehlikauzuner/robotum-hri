import yaml
from pathlib import Path

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid


MAP_DIR = Path('/home/mehlika/hri_ws/maps')
MAP_NAME = 'my_map'


class MapPublisher(Node):

    def __init__(self):
        super().__init__('map_publisher')

        yaml_path = MAP_DIR / f'{MAP_NAME}.yaml'

        with open(yaml_path, 'r') as file:
            map_config = yaml.safe_load(file)

        self.map = OccupancyGrid()

        self.map.header.frame_id = 'map'

        self.map.info.resolution = float(map_config['resolution'])

        self.map.info.origin.position.x = float(
            map_config['origin'][0]
        )
        self.map.info.origin.position.y = float(
            map_config['origin'][1]
        )
        self.map.info.origin.position.z = 0.0

        image_path = MAP_DIR / map_config['image']

        from PIL import Image

        image = Image.open(image_path).convert('L')

        self.map.info.width = image.width
        self.map.info.height = image.height

        pixels = list(image.getdata())

        data = []

        for pixel in pixels:

            if pixel == 205:
                data.append(-1)

            elif pixel >= 250:
                data.append(0)

            else:
                data.append(100)

        data.reverse()

        self.map.data = data

        self.publisher = self.create_publisher(
            OccupancyGrid,
            '/map',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_map
        )

        self.get_logger().info(
            '================================='
        )
        self.get_logger().info(
            'Loaded saved map successfully'
        )
        self.get_logger().info(
            f'Map: {image_path}'
        )
        self.get_logger().info(
            f'Size: {image.width} x {image.height}'
        )
        self.get_logger().info(
            f'Resolution: {self.map.info.resolution}'
        )
        self.get_logger().info(
            'Publishing on /map'
        )
        self.get_logger().info(
            '================================='
        )

    def publish_map(self):
        self.map.header.stamp.sec = 0
        self.map.header.stamp.nanosec = 0
        self.publisher.publish(self.map)


def main():

    rclpy.init()

    node = MapPublisher()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
