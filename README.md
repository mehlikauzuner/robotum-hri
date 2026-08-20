# Web-Based Human–Robot Interaction Platform

This project is a ROS 2-based Human–Robot Interaction (HRI) platform developed for controlling a simulated robot through Natural Language Processing (NLP).

The system integrates:

- Gazebo simulation
- TurtleBot3 simulation
- SLAM Toolbox for mapping
- Navigation2 (Nav2) for autonomous navigation
- NLP-based command interpretation
- A planner node for converting commands into navigation goals
- Foxglove Bridge for visualization and monitoring
- Custom ROS 2 packages for robot interaction

The project is developed using **ROS 2 Lyrical**.

---

# System Architecture

The basic command flow is:

```text
User Command
     ↓
NLP Node
     ↓
/user_command
     ↓
Planner Node
     ↓
NavigateToPose Action
     ↓
Nav2
     ↓
Robot Movement
```

At the same time:

```text
Gazebo
   ↓
Laser Scan + Odometry + TF
   ↓
SLAM Toolbox
   ↓
Map
   ↓
Nav2 Navigation
```

---

# Requirements

The project was developed and tested with:

- Ubuntu
- ROS 2 Lyrical
- Python 3
- Gazebo
- TurtleBot3 Gazebo
- Foxglove Bridge

Check your ROS distribution:

```bash
echo $ROS_DISTRO
```

Expected output:

```text
lyrical
```

---

# Clone the Repository

Clone the project:

```bash
git clone https://bison.iitis.pl/nkelesoglu/web-based-human-robot-interaction-platform.git
```

Enter the repository:

```bash
cd web-based-human-robot-interaction-platform
```

The repository contains the custom project packages and configuration files.

---

# Create the ROS 2 Workspace

Create a ROS 2 workspace:

```bash
mkdir -p ~/hri_ws/src
```

Copy the project packages into the workspace:

```bash
cp -r ~/web-based-human-robot-interaction-platform/src/* ~/hri_ws/src/
```

Check the workspace:

```bash
ls ~/hri_ws/src
```

You should see packages similar to:

```text
cmd_vel_converter
hri_bringup
map_tools
nlp
planner
slam_toolbox
```

---

# Navigation2 (Nav2)

Navigation2 is required for autonomous navigation.

Nav2 is **not included as a project package in the repository**. It must be added separately to the ROS 2 workspace.

Go to the workspace source directory:

```bash
cd ~/hri_ws/src
```

Clone the ROS 2 Lyrical branch of Navigation2:

```bash
git clone -b lyrical https://github.com/ros-navigation/navigation2.git
```

After cloning, the workspace should look similar to:

```text
hri_ws/
└── src/
    ├── cmd_vel_converter
    ├── hri_bringup
    ├── map_tools
    ├── navigation2
    ├── nlp
    ├── planner
    └── slam_toolbox
```

Nav2 is installed from source inside:

```text
~/hri_ws/src/navigation2
```

---

# SLAM Toolbox

SLAM Toolbox is included in the project and copied into the workspace.

Its location is:

```text
~/hri_ws/src/slam_toolbox
```

SLAM Toolbox is used for online mapping.

The project uses the following custom configuration file:

```text
hri_bringup/config/mapper_params_hri.yaml
```

SLAM Toolbox receives:

- Laser scan data
- Odometry
- TF transforms

and generates a map while the robot moves through the environment.

---

# TurtleBot3 Gazebo

The project uses TurtleBot3 Gazebo for simulation.

Install it if necessary:

```bash
sudo apt update
sudo apt install ros-lyrical-turtlebot3-gazebo
```

Check the installation:

```bash
ros2 pkg prefix turtlebot3_gazebo
```

---

# Foxglove Bridge

Foxglove Bridge is used to connect ROS 2 topics to Foxglove for visualization and debugging.

Install it if necessary:

```bash
sudo apt update
sudo apt install ros-lyrical-foxglove-bridge
```

Check the installation:

```bash
ros2 pkg prefix foxglove_bridge
```

The bridge is started as part of the project launch system.

---

# Install Dependencies

Go to the workspace:

```bash
cd ~/hri_ws
```

If rosdep has not been initialized before:

```bash
sudo rosdep init
rosdep update
```

Install dependencies:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

---

# Build the Workspace

Build all packages:

```bash
cd ~/hri_ws
colcon build --symlink-install
```

After the build finishes:

```bash
source install/setup.bash
```

For every new terminal, source ROS 2 and the workspace:

```bash
source /opt/ros/lyrical/setup.bash
source ~/hri_ws/install/setup.bash
```

---

# Running the Complete System

Open a new terminal.

Go to the workspace:

```bash
cd ~/hri_ws
```

Source ROS 2:

```bash
source /opt/ros/lyrical/setup.bash
```

Source the workspace:

```bash
source install/setup.bash
```

Start the complete HRI simulation:

```bash
ros2 launch hri_bringup hri_sim.launch.py
```

The main launch file is:

```text
hri_bringup/launch/hri_sim.launch.py
```

The system starts the main components required by the HRI simulation, including:

- Gazebo
- SLAM Toolbox
- Navigation2
- Foxglove Bridge
- Command Velocity Converter
- Planner Node

---

# NLP Node

The NLP package is responsible for interpreting user commands.

The general command flow is:

```text
User Input
    ↓
NLP Processing
    ↓
/user_command
    ↓
Planner
```

The NLP package is located at:

```text
~/hri_ws/src/nlp
```

---

# Planner Node

The planner receives commands from the NLP component and converts them into navigation goals.

The general flow is:

```text
/user_command
      ↓
Planner
      ↓
NavigateToPose Goal
      ↓
/navigate_to_pose
      ↓
Nav2
```

The planner package is located at:

```text
~/hri_ws/src/planner
```

You can inspect the navigation action with:

```bash
ros2 action info /navigate_to_pose
```

---

# Nav2 Configuration

The project uses a custom Nav2 configuration file:

```text
hri_bringup/config/nav2_params.yaml
```

This project-specific configuration is separate from the default Nav2 configuration inside:

```text
navigation2/nav2_bringup/params/nav2_params.yaml
```

An important robot parameter is:

```yaml
robot_radius: 0.22
```

This value is configured for both:

- Local Costmap
- Global Costmap

The Nav2 configuration includes parameters related to:

- Local costmap
- Global costmap
- Obstacle detection
- Inflation layers
- Laser scan processing
- Navigation controllers
- Navigation planning

---

# SLAM and Navigation Pipeline

The navigation system works as follows:

```text
Gazebo
   ↓
Robot Sensors
   ↓
/scan + /odom + TF
   ↓
SLAM Toolbox
   ↓
/map
   ↓
Nav2
   ↓
NavigateToPose
   ↓
Robot Movement
```

SLAM Toolbox creates the map while the robot moves.

Nav2 uses the map, sensor data, and robot pose to calculate and execute navigation paths.

---

# Foxglove Visualization

Foxglove can be used to visualize and debug the ROS 2 system.

Useful topics include:

```text
/map
/scan
/tf
/odom
/cmd_vel
```

Foxglove can be used to inspect:

- Robot movement
- Laser scan data
- Generated maps
- TF frames
- Odometry
- Navigation data

---

# Useful ROS Commands

Check active nodes:

```bash
ros2 node list
```

Check available topics:

```bash
ros2 topic list
```

Check available actions:

```bash
ros2 action list
```

Check the navigation action:

```bash
ros2 action info /navigate_to_pose
```

Check Nav2:

```bash
ros2 pkg prefix nav2_bringup
```

Check SLAM Toolbox:

```bash
ros2 pkg prefix slam_toolbox
```

Check TurtleBot3 Gazebo:

```bash
ros2 pkg prefix turtlebot3_gazebo
```

Check Foxglove Bridge:

```bash
ros2 pkg prefix foxglove_bridge
```

---

# Project Structure

After completing the installation, the workspace should look similar to:

```text
hri_ws/
├── src/
│   ├── cmd_vel_converter/
│   ├── hri_bringup/
│   │   ├── launch/
│   │   │   └── hri_sim.launch.py
│   │   └── config/
│   │       ├── mapper_params_hri.yaml
│   │       └── nav2_params.yaml
│   ├── map_tools/
│   ├── navigation2/
│   ├── nlp/
│   ├── planner/
│   └── slam_toolbox/
│
├── build/
├── install/
└── log/
```

---

# Development

After modifying a ROS 2 package:

```bash
cd ~/hri_ws
colcon build --symlink-install
source install/setup.bash
```

Then restart the system:

```bash
ros2 launch hri_bringup hri_sim.launch.py
```

---

# Troubleshooting

## Nav2 is not found

Check:

```bash
ros2 pkg prefix nav2_bringup
```

If Nav2 is not found, make sure it exists inside:

```text
~/hri_ws/src/navigation2
```

Then rebuild:

```bash
cd ~/hri_ws
colcon build --symlink-install
source install/setup.bash
```

## SLAM Toolbox is not found

Check:

```bash
ros2 pkg prefix slam_toolbox
```

Then make sure the workspace is sourced:

```bash
source /opt/ros/lyrical/setup.bash
source ~/hri_ws/install/setup.bash
```

## TurtleBot3 Gazebo is not found

Install:

```bash
sudo apt install ros-lyrical-turtlebot3-gazebo
```

## Foxglove Bridge is not found

Install:

```bash
sudo apt install ros-lyrical-foxglove-bridge
```

---

# Summary

This project combines custom Human–Robot Interaction components with the ROS 2 navigation ecosystem.

The main technologies are:

- ROS 2 Lyrical
- Gazebo
- TurtleBot3
- SLAM Toolbox
- Navigation2
- NLP
- Foxglove Bridge

The main project packages are:

```text
cmd_vel_converter
hri_bringup
map_tools
nlp
planner
slam_toolbox
```

Navigation2 is installed separately from source inside:

```text
~/hri_ws/src/navigation2
```

The complete system can be started with:

```bash
ros2 launch hri_bringup hri_sim.launch.py
```