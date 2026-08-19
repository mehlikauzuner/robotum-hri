import math
from pathlib import Path

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
import yaml
from PIL import Image


# ============================================================
# MAP CONFIGURATION
# ============================================================

MAP_DIR = Path('/home/mehlika/hri_ws/maps')
MAP_NAME = 'my_map'


class MapSaver(Node):

    def __init__(self):
        super().__init__('map_saver')

        # Make sure the maps directory exists
        MAP_DIR.mkdir(parents=True, exist_ok=True)

        self.subscription = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            10
        )

        self.saved = False

        self.get_logger().info(
            f'Waiting for /map... Saving as: {MAP_NAME}'
        )

    def map_callback(self, msg):

        if self.saved:
            return

        width = msg.info.width
        height = msg.info.height

        self.get_logger().info(
            f'Received map: {width} x {height}, '
            f'resolution: {msg.info.resolution}'
        )

        # ----------------------------------------------------
        # Convert OccupancyGrid values to grayscale
        #
        # -1  = unknown   -> 205
        #  0  = free      -> 254
        #  1-100 = occupied -> 0
        # ----------------------------------------------------

        pixels = []

        for value in msg.data:

            if value == -1:
                pixels.append(205)

            elif value == 0:
                pixels.append(254)

            else:
                pixels.append(0)

        # ----------------------------------------------------
        # Create PGM image
        # ----------------------------------------------------

        image = Image.new('L', (width, height))
        image.putdata(pixels)

        # ROS map origin is bottom-left.
        # Image coordinates start from top-left.
        image = image.transpose(
            Image.Transpose.FLIP_TOP_BOTTOM
        )

        pgm_path = MAP_DIR / f'{MAP_NAME}.pgm'
        yaml_path = MAP_DIR / f'{MAP_NAME}.yaml'

        image.save(pgm_path)

        # ----------------------------------------------------
        # Calculate yaw from map origin quaternion
        # ----------------------------------------------------

        q = msg.info.origin.orientation

        siny_cosp = 2.0 * (
            q.w * q.z + q.x * q.y
        )

        cosy_cosp = 1.0 - 2.0 * (
            q.y * q.y + q.z * q.z
        )

        yaw = math.atan2(siny_cosp, cosy_cosp)

        # ----------------------------------------------------
        # YAML map configuration
        # ----------------------------------------------------

        yaml_data = {
            'image': pgm_path.name,
            'resolution': float(msg.info.resolution),
            'origin': [
                float(msg.info.origin.position.x),
                float(msg.info.origin.position.y),
                float(yaw)
            ],
            'negate': 0,
            'occupied_thresh': 0.65,
            'free_thresh': 0.25
        }

        with open(yaml_path, 'w') as file:
            yaml.safe_dump(
                yaml_data,
                file,
                default_flow_style=False
            )

        # ----------------------------------------------------
        # Done
        # ----------------------------------------------------

        self.get_logger().info(
            '========================================'
        )

        self.get_logger().info(
            f'MAP SAVED SUCCESSFULLY'
        )

        self.get_logger().info(
            f'PGM : {pgm_path}'
        )

        self.get_logger().info(
            f'YAML: {yaml_path}'
        )

        self.get_logger().info(
            '========================================'
        )

        self.saved = True


def main():

    rclpy.init()

    node = MapSaver()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()