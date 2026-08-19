import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():

    turtlebot3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    slam_toolbox = get_package_share_directory('slam_toolbox')
    nav2_bringup = get_package_share_directory('nav2_bringup')
    hri_bringup = get_package_share_directory('hri_bringup')

    # ---------------------------------------------------------
    # 1. Gazebo
    # ---------------------------------------------------------
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                turtlebot3_gazebo,
                'launch',
                'turtlebot3_world.launch.py'
            )
        )
    )

    # ---------------------------------------------------------
    # 2. SLAM
    # ---------------------------------------------------------
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                slam_toolbox,
                'launch',
                'online_async_launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': os.path.join(
                hri_bringup,
                'config',
                'mapper_params_hri.yaml'
            )
        }.items()
    )

    # ---------------------------------------------------------
    # 3. Nav2
    # Start after Gazebo + SLAM have had time to initialize
    # ---------------------------------------------------------
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                nav2_bringup,
                'launch',
                'navigation_launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'autostart': 'true',
            'params_file': os.path.join(
                hri_bringup,
                'config',
                'nav2_params.yaml'
            )
        }.items()
    )

    # ---------------------------------------------------------
    # 4. Other nodes
    # ---------------------------------------------------------
    foxglove_bridge = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        output='screen'
    )

    cmd_vel_converter = Node(
        package='cmd_vel_converter',
        executable='converter',
        output='screen'
    )

    planner_node = Node(
        package='planner',
        executable='planner',
        output='screen'
    )

    # ---------------------------------------------------------
    # Launch order
    # ---------------------------------------------------------
    return LaunchDescription([
        # Start Gazebo first
        gazebo_launch,

        # Give Gazebo time to publish clock / TF / scan / odom
        TimerAction(
            period=5.0,
            actions=[
                slam_launch
            ]
        ),

        # Give SLAM time to initialize before Nav2
        TimerAction(
            period=12.0,
            actions=[
                nav2_launch
            ]
        ),

        foxglove_bridge,
        cmd_vel_converter,
        planner_node,
    ])