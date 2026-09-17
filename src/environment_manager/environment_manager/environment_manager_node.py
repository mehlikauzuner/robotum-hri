from pathlib import Path
from functools import partial
import json
import re
import subprocess

import rclpy
from rclpy.node import Node
from slam_toolbox.srv import SaveMap
from environment_manager_interfaces.srv import SelectEnvironment, SaveEnvironment, ListEnvironments, StartMapping, FinishMapping, DeleteEnvironment
from nav2_msgs.srv import LoadMap
from std_msgs.msg import String


class EnvironmentManager(Node):

    def __init__(self):
        super().__init__('environment_manager')

        self.environments_dir = (
            Path.home() / 'robotum-hri-github' / 'environments'
        )

        self.environments_dir.mkdir(parents=True, exist_ok=True)
        self.current_environment_pub = self.create_publisher(String, '/current_environment', 10)

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

        self.list_environments_service = self.create_service(
            ListEnvironments,
            '/list_environments',
            self.handle_list_environments
        )

        self.save_environment_service = self.create_service(
            SaveEnvironment,
            '/save_environment',
            self.handle_save_environment
        )

        self.start_mapping_service = self.create_service(
            StartMapping,
            '/start_mapping',
            self.handle_start_mapping
        )

        self.finish_mapping_service = self.create_service(
            FinishMapping,
            '/finish_mapping',
            self.handle_finish_mapping
        )

        self.delete_environment_service = self.create_service(
            DeleteEnvironment,
            '/delete_environment',
            self.handle_delete_environment
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

        self.current_environment_timer = self.create_timer(1.0, self.publish_current_environment)


    def publish_current_environment(self):
        if self.current_environment:
            msg = String()
            msg.data = self.current_environment
            self.current_environment_pub.publish(msg)


    def handle_list_environments(self, request, response):
        response.environments = [
            path.name
            for path in self.environments_dir.iterdir()
            if path.is_dir()
        ]
        response.environments.sort()
        return response


    def handle_save_environment(self, request, response):
        future = self.save_environment(request.environment_name)

        if future is None:
            response.success = False
            response.message = (
                f'Failed to start saving environment: '
                f'{request.environment_name}'
            )
            return response

        response.success = True
        response.message = (
            f'Environment map saving started: '
            f'{request.environment_name}'
        )

        future.add_done_callback(
            partial(
                self.handle_map_save_result,
                request.environment_name
            )
        )

        return response


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


    def handle_delete_environment(self, request, response):
        environment_name = request.environment_name.strip()

        if not re.fullmatch(r'[A-Za-z0-9_-]+', environment_name):
            response.success = False
            response.message = 'Invalid environment name.'
            return response

        if environment_name == self.current_environment:
            response.success = False
            response.message = 'Cannot delete the current environment.'
            return response

        environment_dir = self.environments_dir / environment_name

        if not environment_dir.is_dir():
            response.success = False
            response.message = (
                f'Environment "{environment_name}" does not exist.'
            )
            return response

        try:
            import shutil
            shutil.rmtree(environment_dir)

            response.success = True
            response.message = (
                f'Environment "{environment_name}" deleted successfully.'
            )

            self.get_logger().info(
                f'Environment deleted: {environment_name}'
            )

        except Exception as error:
            response.success = False
            response.message = (
                f'Failed to delete environment: {error}'
            )
            self.get_logger().error(
                f'Failed to delete environment "{environment_name}": {error}'
            )

        return response

    def handle_start_mapping(self, request, response):
        self.get_logger().info(
            'Start mapping request received.'
        )

        if hasattr(self, 'mapping_process') and self.mapping_process is not None:
            if self.mapping_process.poll() is None:
                response.success = False
                response.message = 'Mapping is already running.'
                return response

        command = [
            'python3',
            '/home/mehlika/robotum-hri-github/src/environment_manager/environment_manager/mapping_supervisor.py',
        ]

        try:
            self.mapping_process = subprocess.Popen(
                command,
                cwd='/home/mehlika/robotum-hri-github',
            )

            response.success = True
            response.message = 'Mapping process started.'
            self.get_logger().info(
                f'Mapping process started with PID {self.mapping_process.pid}.'
            )

        except Exception as error:
            self.mapping_process = None
            response.success = False
            response.message = (
                f'Failed to start mapping: {error}'
            )
            self.get_logger().error(
                f'Failed to start mapping: {error}'
            )

        return response


    def handle_finish_mapping(self, request, response):
        self.get_logger().info(
            'Finish mapping request received.'
        )

        if not hasattr(self, 'mapping_process') or self.mapping_process is None:
            response.success = False
            response.message = 'No mapping process is running.'
            return response

        if self.mapping_process.poll() is not None:
            self.mapping_process = None
            response.success = False
            response.message = 'Mapping process is not running.'
            return response

        self.mapping_finished = True

        response.success = True
        response.message = (
            'Mapping finished. Enter a name to save the environment.'
        )

        self.get_logger().info(
            'Mapping marked as finished. SLAM remains active until save.'
        )

        return response

    def handle_map_save_result(self, environment_name, future):
        try:
            result = future.result()

            if result.result == 0:
                self.get_logger().info(
                    'Environment map saved successfully.'
                )

                environment_dir = (
                    self.environments_dir / environment_name
                )

                metadata = {
                    "name": environment_name,
                    "type": "room",
                    "room": environment_name,
                    "map": "map.yaml",
                    "semantic_map": "semantic_map.json"
                }

                metadata_path = environment_dir / "metadata.json"

                with metadata_path.open("w", encoding="utf-8") as file:
                    json.dump(metadata, file, indent=2)
                    file.write("\n")

                semantic_map = {
                    "environment": environment_name,
                    "objects": []
                }

                semantic_map_path = (
                    environment_dir / "semantic_map.json"
                )

                with semantic_map_path.open("w", encoding="utf-8") as file:
                    json.dump(semantic_map, file, indent=2)
                    file.write("\n")

                self.get_logger().info(
                    f'Environment metadata created: {environment_name}'
                )

                if (
                    hasattr(self, 'mapping_process')
                    and self.mapping_process is not None
                    and self.mapping_process.poll() is None
                ):
                    self.get_logger().info(
                        'Stopping mapping process after successful save.'
                    )

                    try:
                        self.mapping_process.terminate()
                        self.mapping_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.mapping_process.kill()
                        self.mapping_process.wait()
                    finally:
                        self.mapping_process = None

                self.mapping_finished = False
            else:
                self.get_logger().error(
                    f'Environment map save failed. '
                    f'Result code: {result.result}'
                )

        except Exception as error:
            self.get_logger().error(
                f'Environment map save request failed: {error}'
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

        if not self.save_map_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(
                '/slam_toolbox/save_map service is not available.'
            )
            return None

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
