from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    nav2_bringup = get_package_share_directory('nav2_bringup')

    map_file = LaunchConfiguration('map')

    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                nav2_bringup,
                'launch',
                'localization_launch.py'
            )
        ),
        launch_arguments={
            'map': map_file,
            'use_sim_time': 'true',
            'autostart': 'true',
            'params_file': os.path.join(
                nav2_bringup,
                'params',
                'nav2_params.yaml'
            ),
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            description='Full path to environment map.yaml'
        ),
        localization_launch,
    ])
