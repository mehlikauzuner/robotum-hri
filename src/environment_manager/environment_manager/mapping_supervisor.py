import os
import signal
import subprocess
import sys


MANAGERS = [
    (
        'Navigation',
        '/lifecycle_manager_navigation/manage_nodes',
    ),
    (
        'Localization',
        '/lifecycle_manager_localization/manage_nodes',
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
        '{command: 1}',
    ]

    try:
        result = subprocess.run(
            command,
            cwd='/home/mehlika/robotum-hri-github',
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(
            f'[mapping_supervisor] {name} shutdown timed out.',
            file=sys.stderr,
        )
        return False

    if result.returncode != 0:
        print(
            f'[mapping_supervisor] Failed to shutdown {name}: '
            f'{result.stderr.strip()}',
            file=sys.stderr,
        )
        return False

    print(f'[mapping_supervisor] {name} shut down.')
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
        mapping_env = os.environ.copy()
        mapping_env['FASTDDS_BUILTIN_TRANSPORTS'] = 'UDPv4'

        process = subprocess.Popen(
            [
                'ros2',
                'launch',
                'hri_bringup',
                'mapping_session.launch.py',
            ],
            cwd='/home/mehlika/robotum-hri-github',
            env=mapping_env,
            start_new_session=True,
        )
    except Exception as error:
        print(
            f'[mapping_supervisor] Failed to start mapping: {error}',
            file=sys.stderr,
        )
        return 1

    def handle_signal(signum, frame):
        print(
            f'[mapping_supervisor] Received signal {signum}. '
            'Stopping mapping process group...'
        )
        try:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                print(
                    f'[mapping_supervisor] Mapping process group '
                    f'{process.pid} terminated.'
                )
        except ProcessLookupError:
            pass
        except Exception as error:
            print(
                f'[mapping_supervisor] Failed to stop mapping process group: {error}',
                file=sys.stderr,
            )
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print(
        f'[mapping_supervisor] Mapping session started '
        f'(PID {process.pid}).'
    )

    process.wait()
    return 0


if __name__ == '__main__':
    sys.exit(main())
