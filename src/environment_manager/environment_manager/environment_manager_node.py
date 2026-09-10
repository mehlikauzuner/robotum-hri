from pathlib import Path
import json
import re

import rclpy
from rclpy.node import Node
from slam_toolbox.srv import SaveMap
from environment_manager_interfaces.srv import SelectEnvironment
from nav2_msgs.srv import LoadMap


class EnvironmentManager(Node):

    def __init__(self):
        super().__init__('environment_manager')

        self.environments_dir = (
            Path.home() / 'robotum-hri-github' / 'environments'
        )

        self.environments_dir.mkdir(parents=True, exist_ok=True)

        self.current_environment_file = (
            self.environments_dir / 'current_environment'
        )

        self.current_environment = None

        if self.current_environment_file.exists():
            current_name = (
                self.current_environment_file
                .read_text(encoding='utf-8')
                .strip()
            )

            if current_name:
                current_dir = self.environments_dir / current_name

                if current_dir.is_dir():
                    self.current_environment = current_name
                    self.get_logger().info(
                        f'Current environment: {self.current_environment}'
                    )
                else:
                    self.get_logger().warning(
                        f'Current environment "{current_name}" '
                        f'does not exist.'
                    )
            else:
                self.get_logger().warning(
                    'current_environment file is empty.'
                )
        else:
            self.get_logger().warning(
                'current_environment file not found.'
            )

        self.select_environment_service = self.create_service(
            SelectEnvironment,
            '/select_environment',
            self.handle_select_environment
        )

        self.load_map_client = self.create_client(
            LoadMap,
            '/map_server/load_map'
        )

        self.save_map_client = self.create_client(
            SaveMap,
            '/slam_toolbox/save_map'
        )

        environments = sorted(
            path.name
            for path in self.environments_dir.iterdir()
            if path.is_dir()
        )

        if environments:
            self.get_logger().info(
                f'Available environments: {", ".join(environments)}'
            )

            for environment_name in environments:
                metadata_path = (
                    self.environments_dir
                    / environment_name
                    / 'metadata.json'
                )

                if metadata_path.exists():
                    try:
                        with metadata_path.open('r', encoding='utf-8') as file:
                            metadata = json.load(file)

                        self.get_logger().info(
                            f'Environment "{environment_name}" metadata loaded: '
                            f'type={metadata.get("type")}, '
                            f'room={metadata.get("room")}'
                        )
                    except (json.JSONDecodeError, OSError) as error:
                        self.get_logger().error(
                            f'Could not read metadata for '
                            f'"{environment_name}": {error}'
                        )
                else:
                    self.get_logger().warning(
                        f'No metadata.json found for "{environment_name}"'
                    )
        else:
            self.get_logger().info('No environments found.')


    def handle_select_environment(self, request, response):
        success = self.select_environment(request.environment_name)

        if not success:
            response.success = False
            response.message = (
                f'Failed to select environment: {request.environment_name}'
            )
            return response

        map_future = self.load_environment_map(request.environment_name)

        if map_future is False:
            response.success = False
            response.message = (
                f'Failed to start map loading: {request.environment_name}'
            )
            return response

        response.success = True
        response.message = (
            f'Environment selected and map loading started: '
            f'{request.environment_name}'
        )

        return response


    def load_environment_map(self, environment_name):
        map_path = (
            self.environments_dir
            / environment_name
            / 'map.yaml'
        )

        if not map_path.exists():
            self.get_logger().error(
                f'Map file not found: {map_path}'
            )
            return False

        if not self.load_map_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(
                '/map_server/load_map service is not available.'
            )
            return False

        request = LoadMap.Request()
        request.map_url = str(map_path)

        self.get_logger().info(
            f'Loading map: {map_path}'
        )

        future = self.load_map_client.call_async(request)
        future.add_done_callback(self.handle_map_load_result)

        return future


    def handle_map_load_result(self, future):
        try:
            result = future.result()

            if result.result == 0:
                self.get_logger().info(
                    'Map loaded successfully.'
                )
            else:
                self.get_logger().error(
                    f'Map load failed. Result code: {result.result}'
                )

        except Exception as error:
            self.get_logger().error(
                f'Map load request failed: {error}'
            )


    def select_environment(self, environment_name):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', environment_name):
            self.get_logger().error(
                f'Invalid environment name: {environment_name}'
            )
            return False

        environment_dir = self.environments_dir / environment_name

        if not environment_dir.is_dir():
            self.get_logger().error(
                f'Environment not found: {environment_name}'
            )
            return False

        metadata_path = environment_dir / 'metadata.json'

        if not metadata_path.exists():
            self.get_logger().error(
                f'No metadata.json found for environment: '
                f'{environment_name}'
            )
            return False

        try:
            with metadata_path.open('r', encoding='utf-8') as file:
                metadata = json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            self.get_logger().error(
                f'Could not read metadata for '
                f'"{environment_name}": {error}'
            )
            return False

        self.current_environment = environment_name

        self.current_environment_file.write_text(
            environment_name + '\n',
            encoding='utf-8'
        )

        self.get_logger().info(
            f'Environment selected: {environment_name}'
        )
        self.get_logger().info(
            f'Room: {metadata.get("room")}'
        )
        self.get_logger().info(
            f'Map: {metadata.get("map")}'
        )

        return True


    def save_environment(self, environment_name):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', environment_name):
            self.get_logger().error(
                f'Invalid environment name: {environment_name}'
            )
            return None

        environment_dir = self.environments_dir / environment_name
        environment_dir.mkdir(parents=True, exist_ok=True)

        map_path = environment_dir / 'map'

        request = SaveMap.Request()
        request.name.data = str(map_path)

        self.get_logger().info(
            f'Saving map for environment: {environment_name}'
        )

        future = self.save_map_client.call_async(request)

        return future


def main(args=None):
    rclpy.init(args=args)

    node = EnvironmentManager()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
