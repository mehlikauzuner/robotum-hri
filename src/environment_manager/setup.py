from setuptools import find_packages, setup

package_name = 'environment_manager'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mehlika',
    maintainer_email='mehlika@example.com',
    description='Environment manager for Robotum HRI',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'environment_manager_node = environment_manager.environment_manager_node:main',
        ],
    },
)
