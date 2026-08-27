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

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                turtlebot3_gazebo,
                'launch',
                'turtlebot3_world.launch.py'
            )
        )
    )

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

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                hri_bringup,
                'launch',
                'navigation_no_collision.launch.py'
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

    gz_bridge = Node(
        package='ros_gz_bridge',
        parameters=[{'use_sim_time': True}],
        executable='parameter_bridge',
        arguments=[
            '--config',
            os.path.join(
                hri_bringup,
                'config',
                'bridge.yaml'
            )
        ],
        output='screen'
    )

    foxglove_bridge = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        output='screen'
    )

    cmd_vel_converter = Node(
        package='cmd_vel_converter',
        executable='converter',
        output='screen',
        remappings=[
            ('cmd_vel', '/cmd_vel_unsafe')
        ]
    )

    cmd_vel_mux = Node(
        package='cmd_vel_mux',
        executable='mux',
        name='cmd_vel_mux',
        output='screen'
    )

    direction_safety = Node(
        package='direction_safety',
        executable='direction_safety',
        name='direction_safety',
        output='screen'
    )

    semantic_map_node = Node(
        package='semantic_map',
        executable='semantic_map_node',
        output='screen'
    )

    planner_node = Node(
        package='planner',
        executable='planner',
        output='screen'
    )

    return LaunchDescription([

        gazebo_launch,

        TimerAction(
            period=5.0,
            actions=[
                slam_launch
            ]
        ),

        TimerAction(
            period=12.0,
            actions=[
                nav2_launch
            ]
        ),

        gz_bridge,
        foxglove_bridge,
        cmd_vel_converter,
        cmd_vel_mux,
        direction_safety,
        semantic_map_node,
        planner_node,
    ])