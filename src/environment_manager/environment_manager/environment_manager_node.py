from pathlib import Path
from functools import partial
import json
import re
import subprocess
import os
import signal

import rclpy
from rclpy.node import Node
from slam_toolbox.srv import SaveMap
from environment_manager_interfaces.srv import SelectEnvironment, SaveEnvironment, ListEnvironments, StartMapping, FinishMapping, DeleteEnvironment
from nav2_msgs.srv import LoadMap
from std_msgs.msg import String
from geometry_msgs.msg import PoseWithCovarianceStamped, PointStamped
from lifecycle_msgs.srv import ChangeState, GetState
import tf2_ros
from rclpy.duration import Duration


class EnvironmentManager(Node):

    def __init__(self):
        super().__init__('environment_manager')
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.environments_dir = (
            Path.home() / 'robotum-hri-github' / 'environments'
        )

        self.environments_dir.mkdir(parents=True, exist_ok=True)
        self.current_environment_pub = self.create_publisher(String, '/current_environment', 10)

        self.initial_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped,
            '/initialpose',
            10
        )

        self.declare_parameter('mode', 'mapping')
        self.mode = self.get_parameter('mode').get_parameter_value().string_value

        self.manual_initial_pose_pending = (self.mode == 'localization')

        self.clicked_point_sub = self.create_subscription(
            PointStamped,
            '/clicked_point',
            self.handle_clicked_point,
            10
        )

        self.amcl_get_state_client = self.create_client(
            GetState,
            '/amcl/get_state'
        )

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

        # Initialize AMCL automatically when localization is launched externally.
        self.initial_pose_timer = self.create_timer(
            1.0,
            self.check_amcl_and_publish_initial_pose,
        )


    def handle_clicked_point(self, msg):
        if not self.manual_initial_pose_pending:
            return

        pose = PoseWithCovarianceStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = 'map'

        pose.pose.pose.position.x = msg.point.x
        pose.pose.pose.position.y = msg.point.y
        pose.pose.pose.position.z = 0.0

        pose.pose.pose.orientation.x = 0.0
        pose.pose.pose.orientation.y = 0.0
        pose.pose.pose.orientation.z = 0.0
        pose.pose.pose.orientation.w = 1.0

        pose.pose.covariance[0] = 0.25
        pose.pose.covariance[7] = 0.25
        pose.pose.covariance[35] = 0.0685

        self.initial_pose_pub.publish(pose)

        self.manual_initial_pose_pending = False

        self.get_logger().info(
            f'Manual initial pose published: '
            f'x={msg.point.x:.3f}, y={msg.point.y:.3f}'
        )


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


    def save_environment(self, environment_name):
        environment_name = environment_name.strip()

        if not re.fullmatch(r'[A-Za-z0-9_-]+', environment_name):
            self.get_logger().error(
                f'Invalid environment name: {environment_name}'
            )
            return None

        environment_dir = self.environments_dir / environment_name

        try:
            environment_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            self.get_logger().error(
                f'Environment already exists: {environment_name}'
            )
            return None
        except OSError as error:
            self.get_logger().error(
                f'Failed to create environment directory: {error}'
            )
            return None

        if not self.save_map_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error(
                'SLAM save_map service is not available.'
            )
            return None

        request = SaveMap.Request()
        request.name.data = str(environment_dir / 'map')

        self.get_logger().info(
            f'Saving environment map to: {request.name.data}'
        )

        return self.save_map_client.call_async(request)

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

        self.manual_initial_pose_pending = True

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

        if not self.save_map_client.wait_for_service(timeout_sec=2.0):
            response.success = False
            response.message = 'SLAM mapping service is not available.'
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
                        self.mapping_process.send_signal(signal.SIGTERM)
                        self.mapping_process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        self.get_logger().warning(
                            'Mapping supervisor did not exit in time. Sending SIGKILL.'
                        )
                        self.mapping_process.kill()
                        self.mapping_process.wait()
                    finally:
                        self.mapping_process = None

                # Make the newly saved environment the active environment.
                self.current_environment = environment_name
                self.current_environment_file.write_text(
                    environment_name,
                    encoding='utf-8'
                )

                self.get_logger().info(
                    f'Current environment updated to: {environment_name}'
                )

                self.get_logger().info(
                    'Map saved successfully. Restarting localization and navigation...'
                )

                for name, service_name in [
                    (
                        'Navigation',
                        '/lifecycle_manager_navigation/manage_nodes',
                    ),
                    (
                        'Localization',
                        '/lifecycle_manager_localization/manage_nodes',
                    ),
                ]:
                    command = [
                        'ros2',
                        'service',
                        'call',
                        service_name,
                        'nav2_msgs/srv/ManageLifecycleNodes',
                        '{command: 2}',
                    ]

                    try:
                        result = subprocess.run(
                            command,
                            cwd='/home/mehlika/robotum-hri-github',
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )

                        if result.returncode == 0:
                            self.get_logger().info(
                                f'{name} restarted successfully.'
                            )
                        else:
                            self.get_logger().error(
                                f'Failed to restart {name}: '
                                f'{result.stderr.strip()}'
                            )

                    except subprocess.TimeoutExpired:
                        self.get_logger().error(
                            f'{name} restart timed out.'
                        )

                # Reload the newly saved environment map after localization is active.
                self.get_logger().info(
                    f'Loading newly saved map: {environment_name}'
                )
                self.load_environment_map(environment_name)

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


    def load_environment_map(self, environment_name):
        environment_dir = self.environments_dir / environment_name
        map_path = environment_dir / 'map.yaml'

        if not map_path.exists():
            self.get_logger().error(
                f'Map file not found: {map_path}'
            )
            return False

        self.get_logger().info(
            f'Loading map for environment: {environment_name}'
        )
        self.get_logger().info(
            f'Using map: {map_path}'
        )

        if not self.load_map_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error(
                'map_server/load_map service is not available.'
            )
            return False

        # Save the robot's current pose BEFORE switching the map.
        # The Gazebo robot stays where it is while the map changes.
        try:
            self.saved_robot_transform = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time(),
                timeout=Duration(seconds=1.0)
            )
            self.get_logger().info(
                f'Saved robot pose before map switch: '
                f'x={self.saved_robot_transform.transform.translation.x:.3f}, '
                f'y={self.saved_robot_transform.transform.translation.y:.3f}'
            )
        except Exception as error:
            self.saved_robot_transform = None
            self.get_logger().warning(
                f'Could not save current robot pose before map switch: {error}'
            )

        request = LoadMap.Request()
        request.map_url = str(map_path)

        future = self.load_map_client.call_async(request)

        def after_map_load(future):
            try:
                result = future.result()

                if result.result == 0:
                    self.get_logger().info(
                        f'Map loaded successfully: {map_path}'
                    )
                    self.publish_initial_pose()
                else:
                    self.get_logger().error(
                        f'Failed to load map: {map_path}'
                    )

            except Exception as error:
                self.get_logger().error(
                    f'Failed to load map: {error}'
                )

        future.add_done_callback(after_map_load)
        return True


    def _start_localization_process(self, map_path):
        command = [
            'ros2',
            'launch',
            'hri_bringup',
            'hri_localization.launch.py',
            f'map:={map_path}',
        ]

        try:
            localization_env = os.environ.copy()
            localization_env['FASTDDS_BUILTIN_TRANSPORTS'] = 'UDPv4'

            self.localization_process = subprocess.Popen(
                command,
                cwd='/home/mehlika/robotum-hri-github',
                env=localization_env,
                start_new_session=True,
            )

            self.get_logger().info(
                f'Localization process started with PID '
                f'{self.localization_process.pid}.'
            )

            # Give AMCL the robot's known starting pose.
            if hasattr(self, 'initial_pose_timer') and self.initial_pose_timer is not None:
                self.initial_pose_timer.cancel()

            self.initial_pose_timer = self.create_timer(
                1.0,
                self.check_amcl_and_publish_initial_pose,
            )

            return self.localization_process

        except Exception as error:
            self.localization_process = None
            self.get_logger().error(
                f'Failed to start localization: {error}'
            )
            return False


    def check_amcl_and_publish_initial_pose(self):
        if not self.amcl_get_state_client.service_is_ready():
            return

        future = self.amcl_get_state_client.call_async(
            GetState.Request()
        )

        def state_callback(future):
            try:
                result = future.result()
                state = result.current_state

                if state.id == 3:
                    self.get_logger().info(
                        'AMCL is active. Publishing initial pose.'
                    )

                    self.publish_initial_pose()

                    if hasattr(self, 'initial_pose_timer'):
                        self.initial_pose_timer.cancel()
                        self.initial_pose_timer = None

            except Exception as error:
                self.get_logger().warning(
                    f'Could not get AMCL lifecycle state: {error}'
                )

        future.add_done_callback(state_callback)


    def publish_initial_pose(self):
        msg = PoseWithCovarianceStamped()

        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'

        transform = getattr(self, 'saved_robot_transform', None)

        if transform is not None:
            msg.pose.pose.position.x = transform.transform.translation.x
            msg.pose.pose.position.y = transform.transform.translation.y
            msg.pose.pose.position.z = transform.transform.translation.z

            msg.pose.pose.orientation.x = transform.transform.rotation.x
            msg.pose.pose.orientation.y = transform.transform.rotation.y
            msg.pose.pose.orientation.z = transform.transform.rotation.z
            msg.pose.pose.orientation.w = transform.transform.rotation.w
        else:
            # Safe fallback: preserve the previous behavior.
            msg.pose.pose.position.x = 0.0
            msg.pose.pose.position.y = 0.0
            msg.pose.pose.position.z = 0.0

            msg.pose.pose.orientation.x = 0.0
            msg.pose.pose.orientation.y = 0.0
            msg.pose.pose.orientation.z = 0.0
            msg.pose.pose.orientation.w = 1.0

        # Reasonable covariance for a known simulated starting pose.
        msg.pose.covariance[0] = 0.25
        msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.0685

        self.initial_pose_pub.publish(msg)

        self.get_logger().info(
            'Initial pose published to AMCL: x=0.0, y=0.0, yaw=0.0'
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

        self.current_environment = environment_name
        self.current_environment_file.write_text(
            environment_name,
            encoding='utf-8'
        )

        self.get_logger().info(
            f'Current environment updated to: {environment_name}'
        )

        return True


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
