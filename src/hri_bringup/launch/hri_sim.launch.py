import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, TimerAction, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import PythonExpression
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    declare_mode = DeclareLaunchArgument('mode', default_value='mapping')
    declare_environment = DeclareLaunchArgument('environment', default_value='test_environment')
    mode = LaunchConfiguration('mode')
    environment = LaunchConfiguration('environment')

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
            'autostart': 'true',
            'slam_params_file': os.path.join(
                hri_bringup,
                'config',
                'mapper_params_hri.yaml'
            )
        }.items()
    )

    environment_map = PathJoinSubstitution([
        "/home/mehlika/robotum-hri-github/environments",
        environment,
        "map.yaml"
    ])

    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                hri_bringup,
                'launch',
                'hri_localization.launch.py'
            )
        ),
        launch_arguments={
            'map': environment_map,
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

    nlp_node = Node(
        package='nlp',
        executable='nlp_node',
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

    robot_status_node = Node(
        package='robot_status',
        executable='robot_status',
        output='screen'
    )

    environment_manager_node = Node(
        package='environment_manager',
        executable='environment_manager_node',
        output='screen'
    )

    whisper_server = ExecuteProcess(
        cmd=[
            '/home/mehlika/whisper-env/bin/python',
            '/home/mehlika/robotum-hri-github/voice_backend/whisper_server.py'
        ],
        output='screen'
    )

    tts_node = Node(
        package='tts',
        executable='tts_node',
        output='screen'
    )

    tts_server = ExecuteProcess(
        cmd=[
            '/home/mehlika/whisper-env/bin/python',
            '/home/mehlika/robotum-hri-github/tts_backend/tts_server.py'
        ],
        output='screen'
    )

    return LaunchDescription([
        declare_mode,
        declare_environment,

        gazebo_launch,

        TimerAction(
            period=5.0,
            condition=IfCondition(PythonExpression(["'", mode, "' == 'mapping'"])),
            actions=[
                slam_launch
            ]
        ),

        TimerAction(
            period=5.0,
            condition=IfCondition(PythonExpression(["'", mode, "' == 'localization'"])),
            actions=[
                localization_launch
            ]
        ),

        TimerAction(
            period=12.0,
            actions=[
                nav2_launch
            ]
        ),

        foxglove_bridge,
        cmd_vel_converter,
        cmd_vel_mux,
        direction_safety,
        nlp_node,
        semantic_map_node,
        planner_node,
        robot_status_node,
        whisper_server,
        tts_node,
        tts_server,
    ])