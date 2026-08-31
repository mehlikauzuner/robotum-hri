from setuptools import find_packages, setup

package_name = 'tts'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mehlikauzuner',
    maintainer_email='uzunermehlika6128@gmail.com',
    description='Robotum Text-to-Speech interface.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'tts_node = tts.tts_node:main',
        ],
    },
)
