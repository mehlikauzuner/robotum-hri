from setuptools import find_packages, setup

package_name = 'map_tools'

setup(
    name=package_name,
    version='0.0.1',
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
    description='Map saving tools for the HRI robot project.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
    'map_saver = map_tools.map_saver:main',
    'map_publisher = map_tools.map_publisher:main',
],
    },
)