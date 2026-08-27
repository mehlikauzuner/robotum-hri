from setuptools import find_packages, setup

package_name = "semantic_map"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages",
         ["resource/" + package_name]),
        ("share/" + package_name,
         ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="mehlika",
    maintainer_email="mehlika@example.com",
    description="Semantic map for robot navigation",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "semantic_map_node = semantic_map.semantic_map_node:main",
        ],
    },
)