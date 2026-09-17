cmake_minimum_required(VERSION 3.8)
project(environment_manager_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SelectEnvironment.srv"
  "srv/SaveEnvironment.srv"
  "srv/AddSemanticObject.srv"
  "srv/ListEnvironments.srv"
  "srv/StartMapping.srv"
        "srv/FinishMapping.srv"
        "srv/DeleteEnvironment.srv"
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
