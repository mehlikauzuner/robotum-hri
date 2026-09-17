import subprocess
import sys


MANAGERS = [
    (
        'Localization',
        '/lifecycle_manager_localization/manage_nodes',
    ),
    (
        'Navigation',
        '/lifecycle_manager_navigation/manage_nodes',
    ),
]


def shutdown_manager(name, service_name):
    print(f'[mapping_supervisor] Shutting down {name}...')

    command = [
        'ros2',
        'service',
        'call',
        service_name,
        'nav2_msgs/srv/ManageLifecycleNodes',
        '{command: 4}',
    ]

    try:
        result = subprocess.run(
            command,
            cwd='/home/mehlika/robotum-hri-github',
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        print(
            f'[mapping_supervisor] {name} shutdown timed out.',
            file=sys.stderr,
        )
        return False

    if result.returncode != 0:
        print(
            f'[mapping_supervisor] Failed to shut down {name}: '
            f'{result.stderr.strip()}',
            file=sys.stderr,
        )
        return False

    print(f'[mapping_supervisor] {name} shutdown completed.')
    return True


def main():
    print('[mapping_supervisor] Starting mapping transition...')

    for name, service_name in MANAGERS:
        if not shutdown_manager(name, service_name):
            print(
                f'[mapping_supervisor] Mapping transition aborted.',
                file=sys.stderr,
            )
            return 1

    print('[mapping_supervisor] Starting SLAM mapping session...')

    try:
        process = subprocess.Popen(
            [
                'ros2',
                'launch',
                'hri_bringup',
                'mapping_session.launch.py',
            ],
            cwd='/home/mehlika/robotum-hri-github',
        )
    except Exception as error:
        print(
            f'[mapping_supervisor] Failed to start mapping: {error}',
            file=sys.stderr,
        )
        return 1

    print(
        f'[mapping_supervisor] Mapping session started '
        f'(PID {process.pid}).'
    )

    process.wait()
    return 0


if __name__ == '__main__':
    sys.exit(main())
