import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    slam_toolbox = get_package_share_directory('slam_toolbox')
    hri_bringup = get_package_share_directory('hri_bringup')

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

    return LaunchDescription([
        slam_launch,
    ])
