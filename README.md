# Web-Based Human–Robot Interaction Platform

A **ROS 2 Lyrical**-based Human–Robot Interaction (HRI) platform for controlling a simulated robot through Natural Language Processing (NLP), either by voice (Whisper) or through a custom Foxglove command panel.

**The system integrates:**

- Gazebo simulation
- TurtleBot3 simulation
- SLAM Toolbox for mapping
- Navigation2 (Nav2) for autonomous navigation
- NLP-based command interpretation
- Semantic map node for resolving named targets
- A planner node for converting commands into navigation goals
- Safety and velocity multiplexing layer
- Text-to-speech (TTS) feedback
- Foxglove Bridge for visualization and monitoring
- Custom ROS 2 packages for robot interaction

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Node, Topic and Service Reference](#2-node-topic-and-service-reference)
3. [Requirements](#3-requirements)
4. [Installation](#4-installation)
5. [Running the Complete System](#5-running-the-complete-system)
6. [Component Details](#6-component-details)
7. [Foxglove Visualization](#7-foxglove-visualization)
8. [Foxglove Command Center Extension](#8-foxglove-command-center-extension)
9. [Useful ROS Commands](#9-useful-ros-commands)
10. [Project Structure](#10-project-structure)
11. [Development](#11-development)
12. [Troubleshooting](#12-troubleshooting)
13. [Summary](#13-summary)

---

## 1. System Architecture

### 1.1 Basic command flow

```text
User Command (voice / text)
        ↓
   Whisper Node  ──►  /user_command
        ↓
     NLP Node    ──►  /parsed_command
        ↓
 Semantic Map Node ──►  /semantic_command
        ↓
   Planner Node
        ↓
NavigateToPose Action (/navigate_to_pose)
        ↓
      Nav2
        ↓
 /cmd_vel_nav ──► cmd_vel_mux_node ──► /cmd_vel_muxed
        ↓
 direction_safety_node (uses /scan)
        ↓
     /cmd_vel
        ↓
  Robot Movement
```

### 1.2 Sensing, mapping and navigation flow

```text
Gazebo
   ↓
Laser Scan + Odometry + TF
   ↓
SLAM Toolbox
   ↓
Map (/map)
   ↓
Nav2 Navigation
   ↓
NavigateToPose
   ↓
Robot Movement
```

---

## 2. Node, Topic and Service Reference

### 2.1 Summary table

| Node | Publishes | Subscribes | Actions / Services |
|------|-----------|------------|--------------------|
| `whisper_node` | `/user_command` | – | – |
| `nlp_node` | `/parsed_command`, `/robot_response` | `/user_command`, `/semantic_targets` | – |
| `semantic_map_node` | `/semantic_command`, `/semantic_targets`, `/semantic_clicked_point`, `/robot_response`, `/robot_status_event` | `/parsed_command`, `/current_environment`, `/clicked_point` | – |
| `planner_node` | `/robot_response`, `/robot_status_event`, `/cmd_vel_unsafe` | `/semantic_command`, `/stop_navigation`, `/odom` | **Action:** `/navigate_to_pose` · **Service:** `/set_navigation_goal` |
| `cmd_vel_mux_node` | `/cmd_vel_muxed` | `/cmd_vel_nav`, `/cmd_vel_llm` | – |
| `direction_safety_node` | `/cmd_vel` | `/cmd_vel_unsafe`, `/cmd_vel_muxed`, `/scan` | – |
| `robot_status_node` | `/robot_status` | `/robot_response`, `/robot_status_event` | – |
| `environment_manager_node` | `/current_environment`, `/initialpose` | `/interaction_mode`, `/clicked_point` | **Services:** environment management + mapping |
| `tts_node` | – | `/robot_response` | – |

### 2.2 Node details

#### `whisper_node`
Speech-to-text entry point of the system.

| Direction | Topics |
|-----------|--------|
| Publisher | `/user_command` |
| Subscriber | None |

#### `nlp_node`
Interprets user commands and turns them into structured commands.

| Direction | Topics |
|-----------|--------|
| Publisher | `/parsed_command`, `/robot_response` |
| Subscriber | `/user_command`, `/semantic_targets` |

#### `semantic_map_node`
Resolves parsed commands against the semantic map (named targets, clicked points, current environment).

| Direction | Topics |
|-----------|--------|
| Publisher | `/semantic_command`, `/semantic_targets`, `/semantic_clicked_point`, `/robot_response`, `/robot_status_event` |
| Subscriber | `/parsed_command`, `/current_environment`, `/clicked_point` |

#### `planner_node`
Converts semantic commands into navigation goals and low-level motion commands.

| Direction | Topics / Interfaces |
|-----------|---------------------|
| Publisher | `/robot_response`, `/robot_status_event`, `/cmd_vel_unsafe` |
| Subscriber | `/semantic_command`, `/stop_navigation`, `/odom` |
| Action | `/navigate_to_pose` |
| Service | `/set_navigation_goal` |

#### `cmd_vel_mux_node`
Multiplexes velocity commands coming from Nav2 and from the LLM/NLP side.

| Direction | Topics |
|-----------|--------|
| Publisher | `/cmd_vel_muxed` |
| Subscriber | `/cmd_vel_nav`, `/cmd_vel_llm` |

#### `direction_safety_node`
Final safety layer: filters velocity commands using laser scan data before they reach the robot.

| Direction | Topics |
|-----------|--------|
| Publisher | `/cmd_vel` |
| Subscriber | `/cmd_vel_unsafe`, `/cmd_vel_muxed`, `/scan` |

#### `robot_status_node`
Aggregates responses and events into a single robot status.

| Direction | Topics |
|-----------|--------|
| Publisher | `/robot_status` |
| Subscriber | `/robot_response`, `/robot_status_event` |

#### `environment_manager_node`
Manages environments and mapping.

| Direction | Topics / Interfaces |
|-----------|---------------------|
| Publisher | `/current_environment`, `/initialpose` |
| Subscriber | `/interaction_mode`, `/clicked_point` |
| Services | Environment management + mapping |

#### `tts_node`
Speaks the robot's responses.

| Direction | Topics |
|-----------|--------|
| Publisher | None |
| Subscriber | `/robot_response` |

### 2.3 Topic-centric view

| Topic | Published by | Subscribed by |
|-------|--------------|---------------|
| `/user_command` | `whisper_node` | `nlp_node` |
| `/parsed_command` | `nlp_node` | `semantic_map_node` |
| `/semantic_targets` | `semantic_map_node` | `nlp_node` |
| `/semantic_command` | `semantic_map_node` | `planner_node` |
| `/semantic_clicked_point` | `semantic_map_node` | – |
| `/clicked_point` | Foxglove / RViz-style click input | `semantic_map_node`, `environment_manager_node` |
| `/current_environment` | `environment_manager_node` | `semantic_map_node` |
| `/initialpose` | `environment_manager_node` | – |
| `/interaction_mode` | – | `environment_manager_node` |
| `/stop_navigation` | – | `planner_node` |
| `/odom` | Gazebo / robot | `planner_node` |
| `/scan` | Gazebo / robot | `direction_safety_node` |
| `/cmd_vel_unsafe` | `planner_node` | `direction_safety_node` |
| `/cmd_vel_nav` | – | `cmd_vel_mux_node` |
| `/cmd_vel_llm` | – | `cmd_vel_mux_node` |
| `/cmd_vel_muxed` | `cmd_vel_mux_node` | `direction_safety_node` |
| `/cmd_vel` | `direction_safety_node` | Robot |
| `/robot_response` | `nlp_node`, `semantic_map_node`, `planner_node` | `robot_status_node`, `tts_node` |
| `/robot_status_event` | `semantic_map_node`, `planner_node` | `robot_status_node` |
| `/robot_status` | `robot_status_node` | – |

*A "–" means no publisher/subscriber is listed in the node table (the source or consumer may be external, e.g. Foxglove, Nav2 or Gazebo).*

### 2.4 Actions and services

| Type | Name | Provided by |
|------|------|-------------|
| Action | `/navigate_to_pose` | Nav2 (goals are sent by `planner_node`) |
| Service | `/set_navigation_goal` | `planner_node` |
| Services | Environment management + mapping | `environment_manager_node` |

---

## 3. Requirements

The project was developed and tested with:

- Ubuntu
- ROS 2 Lyrical
- Python 3
- Gazebo
- TurtleBot3 Gazebo
- Foxglove Bridge
- Foxglove Studio Desktop, Node.js and npm (for the custom panel)

Check your ROS distribution:

```bash
echo $ROS_DISTRO
```

Expected output:

```text
lyrical
```

---

## 4. Installation

### 4.1 Clone the repository

```bash
git clone <REPOSITORY_URL> ~/robotum-hri-github
cd ~/robotum-hri-github
```

Replace `<REPOSITORY_URL>` with the URL of this repository (GitHub or IITiS PAN). The explicit target directory makes the clone end up in `~/robotum-hri-github` regardless of the repository name in the URL.

The repository contains the custom project packages and configuration files.

> **Repository vs. workspace:** `~/robotum-hri-github` is the Git repository (the cloned source). `~/hri_ws` is the separate ROS 2 workspace that is created in the next step, where the packages are copied, built and run. They are two different directories.

### 4.2 Create the ROS 2 workspace

```bash
mkdir -p ~/hri_ws/src
```

Copy the project packages into the workspace:

```bash
cp -r ~/robotum-hri-github/src/* ~/hri_ws/src/
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

### 4.3 Navigation2 (Nav2)

Navigation2 is required for autonomous navigation.

> Nav2 is **not included as a project package in the repository**. It must be added separately to the ROS 2 workspace.

```bash
cd ~/hri_ws/src
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

### 4.4 SLAM Toolbox

SLAM Toolbox is included in the project and copied into the workspace with the other packages.

```text
~/hri_ws/src/slam_toolbox
```

### 4.5 TurtleBot3 Gazebo

The project uses TurtleBot3 Gazebo for simulation. Install it if necessary:

```bash
sudo apt update
sudo apt install ros-lyrical-turtlebot3-gazebo
```

Check the installation:

```bash
ros2 pkg prefix turtlebot3_gazebo
```

### 4.6 Foxglove Bridge

Foxglove Bridge connects ROS 2 topics to Foxglove for visualization and debugging. Install it if necessary:

```bash
sudo apt update
sudo apt install ros-lyrical-foxglove-bridge
```

Check the installation:

```bash
ros2 pkg prefix foxglove_bridge
```

The bridge is started as part of the project launch system.

### 4.7 Install dependencies

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

### 4.8 Build the workspace

```bash
cd ~/hri_ws
colcon build --symlink-install
source install/setup.bash
```

For every new terminal, source ROS 2 and the workspace:

```bash
source /opt/ros/lyrical/setup.bash
source ~/hri_ws/install/setup.bash
```

---

## 5. Running the Complete System

Open a new terminal, then:

```bash
cd ~/hri_ws
source /opt/ros/lyrical/setup.bash
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

## 6. Component Details

### 6.1 NLP Node

The NLP package interprets user commands.

```text
User Input (/user_command)
    ↓
NLP Processing
    ↓
/parsed_command
    ↓
Semantic Map Node → /semantic_command → Planner
```

- Subscribes to `/user_command` (from `whisper_node`) and `/semantic_targets` (known targets from `semantic_map_node`).
- Publishes `/parsed_command` and `/robot_response`.
- Location: `~/hri_ws/src/nlp`

### 6.2 Semantic Map Node

Receives parsed commands and resolves them using the current environment and clicked points, then publishes:

- `/semantic_command` for the planner
- `/semantic_targets` back to the NLP node
- `/semantic_clicked_point`
- `/robot_response` and `/robot_status_event` for feedback

### 6.3 Planner Node

The planner receives semantic commands and converts them into navigation goals.

```text
/semantic_command
      ↓
Planner
      ↓
NavigateToPose Goal
      ↓
/navigate_to_pose
      ↓
Nav2
```

- Also listens to `/stop_navigation` and `/odom`.
- Publishes `/cmd_vel_unsafe`, `/robot_response` and `/robot_status_event`.
- Exposes the `/set_navigation_goal` service.
- Location: `~/hri_ws/src/planner`

Inspect the navigation action with:

```bash
ros2 action info /navigate_to_pose
```

### 6.4 Velocity Pipeline (Mux and Safety)

```text
/cmd_vel_nav ──┐
               ├─► cmd_vel_mux_node ─► /cmd_vel_muxed ─┐
/cmd_vel_llm ──┘                                        ├─► direction_safety_node ─► /cmd_vel ─► Robot
                        /cmd_vel_unsafe ────────────────┤
                        /scan ──────────────────────────┘
```

### 6.5 Environment Manager

`environment_manager_node` publishes `/current_environment` and `/initialpose`, listens to `/interaction_mode` and `/clicked_point`, and provides the environment management and mapping services.

### 6.6 Robot Status and TTS

- `robot_status_node` combines `/robot_response` and `/robot_status_event` into `/robot_status`.
- `tts_node` speaks everything published on `/robot_response`.

### 6.7 SLAM Toolbox

SLAM Toolbox is used for online mapping. It receives:

- Laser scan data
- Odometry
- TF transforms

and generates a map while the robot moves through the environment.

Custom configuration file:

```text
hri_bringup/config/mapper_params_hri.yaml
```

### 6.8 Nav2 Configuration

The project uses a custom Nav2 configuration file:

```text
hri_bringup/config/nav2_params.yaml
```

This is separate from the default Nav2 configuration inside:

```text
navigation2/nav2_bringup/params/nav2_params.yaml
```

An important robot parameter:

```yaml
robot_radius: 0.22
```

This value is configured for both the **Local Costmap** and the **Global Costmap**.

The configuration covers:

- Local costmap
- Global costmap
- Obstacle detection
- Inflation layers
- Laser scan processing
- Navigation controllers
- Navigation planning

### 6.9 SLAM and Navigation Pipeline

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

SLAM Toolbox creates the map while the robot moves. Nav2 uses the map, sensor data and robot pose to calculate and execute navigation paths.

---

## 7. Foxglove Visualization

Foxglove can be used to visualize and debug the ROS 2 system.

Useful topics:

```text
/map
/scan
/tf
/odom
/cmd_vel
/robot_status
/robot_response
```

Foxglove can be used to inspect:

- Robot movement
- Laser scan data
- Generated maps
- TF frames
- Odometry
- Navigation data
- Robot status and responses

---

## 8. Foxglove Command Center Extension

The project includes a custom Foxglove extension located at:

```text
foxglove_extensions/hri-command-center/
```

It provides the custom **ExamplePanel / Robot Command Center** panel used to interact with the Robotum HRI system.

### 8.1 Requirements

- Foxglove Studio Desktop
- Node.js
- npm

Check whether Node.js and npm are installed:

```bash
node -v
npm -v
```

If they are not installed, install them before continuing. npm recommends using a Node.js version manager such as `nvm`.

### 8.2 Install the extension

After cloning the repository, go to the extension directory:

```bash
cd ~/robotum-hri-github/foxglove_extensions/hri-command-center
```

Install the extension dependencies:

```bash
npm install
```

Build and install the extension locally into Foxglove Studio:

```bash
npm run local-install
```

`npm install` installs the dependencies defined by the extension's `package.json`, while `npm run local-install` builds the extension and places the compiled extension in Foxglove's local extensions directory.

### 8.3 Open the panel in Foxglove

1. Open **Foxglove Studio Desktop**.
2. Restart Foxglove Studio if it was already open.
3. Open a layout or visualization.
4. Select **Add Panel**.
5. Select **ExamplePanel**.

The custom panel should now be available in Foxglove.

### 8.4 Updating the extension

If the extension source code is modified:

```bash
cd ~/robotum-hri-github/foxglove_extensions/hri-command-center
npm run local-install
```

Then reload or restart Foxglove Studio to use the updated extension.

---

## 9. Useful ROS Commands

| Purpose | Command |
|---------|---------|
| Active nodes | `ros2 node list` |
| Available topics | `ros2 topic list` |
| Available actions | `ros2 action list` |
| Available services | `ros2 service list` |
| Navigation action info | `ros2 action info /navigate_to_pose` |
| Check Nav2 | `ros2 pkg prefix nav2_bringup` |
| Check SLAM Toolbox | `ros2 pkg prefix slam_toolbox` |
| Check TurtleBot3 Gazebo | `ros2 pkg prefix turtlebot3_gazebo` |
| Check Foxglove Bridge | `ros2 pkg prefix foxglove_bridge` |

Handy debugging examples for the command pipeline:

```bash
ros2 topic echo /user_command
ros2 topic echo /parsed_command
ros2 topic echo /semantic_command
ros2 topic echo /robot_response
ros2 topic echo /robot_status
```

---

## 10. Project Structure

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

Repository-side extension:

```text
foxglove_extensions/
└── hri-command-center/
```

---

## 11. Development

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

After modifying the Foxglove extension, see [Updating the extension](#84-updating-the-extension).

---

## 12. Troubleshooting

### Nav2 is not found

```bash
ros2 pkg prefix nav2_bringup
```

If Nav2 is not found, make sure it exists inside `~/hri_ws/src/navigation2`, then rebuild:

```bash
cd ~/hri_ws
colcon build --symlink-install
source install/setup.bash
```

### SLAM Toolbox is not found

```bash
ros2 pkg prefix slam_toolbox
```

Then make sure the workspace is sourced:

```bash
source /opt/ros/lyrical/setup.bash
source ~/hri_ws/install/setup.bash
```

### TurtleBot3 Gazebo is not found

```bash
sudo apt install ros-lyrical-turtlebot3-gazebo
```

### Foxglove Bridge is not found

```bash
sudo apt install ros-lyrical-foxglove-bridge
```

---

## 13. Summary

This project combines custom Human–Robot Interaction components with the ROS 2 navigation ecosystem.

**Main technologies:**

- ROS 2 Lyrical
- Gazebo
- TurtleBot3
- SLAM Toolbox
- Navigation2
- NLP
- Foxglove Bridge

**Main project packages:**

```text
cmd_vel_converter
hri_bringup
map_tools
nlp
planner
slam_toolbox
```

**Main runtime nodes:**

```text
whisper_node, nlp_node, semantic_map_node, planner_node,
cmd_vel_mux_node, direction_safety_node, robot_status_node,
environment_manager_node, tts_node
```

Navigation2 is installed separately from source inside:

```text
~/hri_ws/src/navigation2
```

The complete system can be started with:

```bash
ros2 launch hri_bringup hri_sim.launch.py
```
