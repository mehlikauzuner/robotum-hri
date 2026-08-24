from setuptools import find_packages, setup

package_name = 'direction_safety'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
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
    description='Direction-aware obstacle safety node',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'direction_safety = direction_safety.direction_safety_node:main',
        ],
    },
)