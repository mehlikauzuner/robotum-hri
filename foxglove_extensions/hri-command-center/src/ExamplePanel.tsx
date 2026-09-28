import { PanelExtensionContext } from "@foxglove/extension";
import { ReactElement, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

interface Props {
  context: PanelExtensionContext;
}

function ExamplePanel({ context }: Props): ReactElement {
  const [command, setCommand] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  const [currentAction, setCurrentAction] = useState("Idle");
  const [queue, setQueue] = useState<string[]>([]);
  const [statusError, setStatusError] = useState("");

  const [robotResponse, setRobotResponse] = useState("Waiting for response...");

  const [showReplyModal, setShowReplyModal] = useState(false);
  const [reply, setReply] = useState("");

  const [clickedX, setClickedX] = useState<number | null>(null);
  const [clickedY, setClickedY] = useState<number | null>(null);
  const [objectName, setObjectName] = useState("");
  const [objectType, setObjectType] = useState("");
  const [currentEnvironment, setCurrentEnvironment] = useState("Unknown");
  const ignoreMappingStatusRef = useRef(false);
  const [showEnvironmentModal, setShowEnvironmentModal] = useState(false);
  const [newEnvironmentName, setNewEnvironmentName] = useState("");
  const [environmentMessage, setEnvironmentMessage] = useState("");
  const [showChangeEnvironmentModal, setShowChangeEnvironmentModal] = useState(false);
  const [availableEnvironments, setAvailableEnvironments] = useState<string[]>([]);
  const [selectedEnvironment, setSelectedEnvironment] = useState("");
  const [isMapping, setIsMapping] = useState(false);
  const [mapTool, setMapTool] = useState<
    "none" | "semantic" | "initial_pose" | "navigation_goal"
  >("none");

  const [initialPoseStep, setInitialPoseStep] = useState<1 | 2>(1);
  const [initialPoseFirstPoint, setInitialPoseFirstPoint] = useState<{
    x: number;
    y: number;
  } | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const commandQueueRef = useRef<string[]>([]);
  const queueDelayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeCommandRef = useRef<string | null>(null);

  const saveSemanticObject = async () => {
    if (!context.callService) {
      console.error("Foxglove service calls are not available.");
      return;
    }

    if (
      clickedX === null ||
      clickedY === null ||
      !objectName.trim() || !objectType.trim()
    ) {
      return;
    }

    try {
      await context.callService("/add_semantic_object", {
        name: objectName.trim(),
        type: objectType.trim() || "unknown",
        x: clickedX,
        y: clickedY,
      });

      setObjectName("");
      setObjectType("");
    } catch (error) {
      console.error("Failed to save semantic object:", error);
    }
  };

  const listEnvironments = async () => {
    if (!context.callService) {
      setEnvironmentMessage("Foxglove service calls are not available.");
      return;
    }

    setEnvironmentMessage("Loading environments...");

    try {
      const result = await context.callService(
        "/list_environments",
        {},
      ) as { environments?: string[] };

      console.log("List environments response:", result);

      const environments = Array.isArray(result.environments)
        ? result.environments
        : [];

      setEnvironmentMessage(
        `DEBUG RESPONSE: ${JSON.stringify(result)}`
      );

      setAvailableEnvironments(environments);

      if (environments.length > 0) {
        setSelectedEnvironment((current) =>
          current && environments.includes(current)
            ? current
            : environments[0] ?? ""
        );
        setEnvironmentMessage(
          `${environments.length} saved environment(s) found.`,
        );
      } else {
        setEnvironmentMessage(
          `No environments returned. Response: ${JSON.stringify(result)}`
        );
      }
    } catch (error) {
      console.error("Failed to list environments:", error);
      setEnvironmentMessage(
        error instanceof Error
          ? `Failed to list environments: ${error.message}`
          : `Failed to list environments: ${String(error)}`,
      );
    }
  };


  const selectEnvironment = async () => {
    const name = selectedEnvironment.trim();

    if (!name || !context.callService) {
      return;
    }

    setEnvironmentMessage(`Loading environment "${name}"...`);

    try {
      const result = await context.callService(
        "/select_environment",
        {
          environment_name: name,
        },
      ) as { success?: boolean; message?: string };

      if (result.success) {
        setEnvironmentMessage(
          result.message || `Environment "${name}" selected successfully.`,
        );
        setShowChangeEnvironmentModal(false);
      } else {
        setEnvironmentMessage(
          result.message || "Failed to select environment.",
        );
      }
    } catch (error) {
      console.error("Failed to select environment:", error);
      setEnvironmentMessage(
        error instanceof Error
          ? error.message
          : String(error),
      );
    }
  };


  const deleteEnvironment = async (name: string) => {
    if (!context.callService) {
      setEnvironmentMessage("Foxglove service calls are not available.");
      return;
    }

    const confirmed = window.confirm(
      `Delete environment "${name}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      const result = await context.callService(
        "/delete_environment",
        {
          environment_name: name,
        },
      ) as { success?: boolean; message?: string };

      if (result.success) {
        setEnvironmentMessage(
          result.message || `Environment "${name}" deleted successfully.`,
        );

        await listEnvironments();
      } else {
        setEnvironmentMessage(
          result.message || `Failed to delete environment "${name}".`,
        );
      }
    } catch (error) {
      console.error("Failed to delete environment:", error);
      setEnvironmentMessage(
        error instanceof Error
          ? error.message
          : String(error),
      );
    }
  };

  const finishMapping = async () => {
    if (!context.callService) {
      setEnvironmentMessage("Foxglove service calls are not available.");
      return;
    }

    setEnvironmentMessage("Finishing mapping...");

    try {
      const result = await context.callService(
        "/finish_mapping",
        {},
      ) as { success?: boolean; message?: string };

      if (result.success) {
        setIsMapping(false);
        setNewEnvironmentName("");
        setEnvironmentMessage(
          result.message || "Mapping finished. Enter a name to save the environment.",
        );
        setShowEnvironmentModal(true);
      } else {
        setEnvironmentMessage(
          result.message || "Failed to finish mapping.",
        );
      }
    } catch (error) {
      console.error("Failed to finish mapping:", error);
      setEnvironmentMessage(
        error instanceof Error
          ? error.message
          : String(error),
      );
    }
  };

  const saveEnvironment = async () => {
    const name = newEnvironmentName.trim();

    if (!name || !context.callService) {
      return;
    }

    setEnvironmentMessage("Saving environment...");

    try {
      const result = await context.callService(
        "/save_environment",
        {
          environment_name: name,
        },
      ) as { success?: boolean; message?: string };

      if (result.success) {
        setIsMapping(false);
        ignoreMappingStatusRef.current = true;
        setCurrentAction("Idle");
        setEnvironmentMessage(
          result.message || "Environment saved successfully.",
        );
        setNewEnvironmentName("");
        setShowEnvironmentModal(false);
      } else {
        setEnvironmentMessage(
          result.message || "Failed to save environment.",
        );
      }
    } catch (error) {
      console.error("Failed to save environment:", error);
      setEnvironmentMessage(
        error instanceof Error
          ? error.message
          : String(error),
      );
    }
  };

  const processNextCommand = () => {
    if (!context.publish) {
      return;
    }

    const nextCommand = commandQueueRef.current.shift();

    console.log(
      "QUEUE PROGRESSION:",
      {
        nextCommand,
        activeCommand: activeCommandRef.current,
        remainingQueue: commandQueueRef.current,
      }
    );

    setQueue([...commandQueueRef.current]);

    if (!nextCommand) {
      activeCommandRef.current = null;
      return;
    }

    activeCommandRef.current = nextCommand;

    context.publish?.("/user_command", {
      data: nextCommand,
    });

  };

  useEffect(() => {
    context.advertise?.("/interaction_mode", "std_msgs/msg/String");
    context.advertise?.("/stop_navigation", "std_msgs/msg/Empty");

    context.subscribe([
      { topic: "/robot_status" },
      { topic: "/robot_response" },
      { topic: "/clicked_point" },
      { topic: "/current_environment" },
    ]);

    context.watch("currentFrame");

    context.onRender = (renderState, done) => {
      for (const message of renderState.currentFrame ?? []) {
        if (message.topic === "/current_environment") {
          const data = message.message as { data?: string };

          if (typeof data.data === "string" && data.data.trim()) {
            setCurrentEnvironment(data.data.trim());
          }
        }

        if (message.topic === "/clicked_point") {
          const data = message.message as {
            point?: {
              x?: number;
              y?: number;
            };
          };

          if (
            typeof data.point?.x === "number" &&
            typeof data.point?.y === "number"
          ) {
            const x = data.point.x;
            const y = data.point.y;

            setClickedX(x);
            setClickedY(y);

            if (mapTool === "navigation_goal") {
        setMapTool("none");

        context.publish?.("/interaction_mode", {
          data: "none",
        });

        return;
      }

      if (mapTool === "initial_pose") {
              if (initialPoseStep === 1) {
                setInitialPoseFirstPoint({ x, y });
                setInitialPoseStep(2);
              } else {
                setInitialPoseStep(1);
                setInitialPoseFirstPoint(null);
              }
            }
          }
        }

        if (message.topic === "/robot_status") {
          const data = message.message as { data?: string };

          try {
            const status = JSON.parse(data.data ?? "{}");

            console.log("ROBOT STATUS RECEIVED:", status);

            if (typeof status.current_action === "string") {
              const action = status.current_action;

              if (ignoreMappingStatusRef.current && action === "Mapping") {
                continue;
              }

              ignoreMappingStatusRef.current = false;
              setCurrentAction(action);
            }

            // Queue progression is based on structured status,
            // not on the wording of the robot response.
            if (status.status === "completed") {
              console.log("QUEUE: Command completed. Waiting 10 seconds...");

              setCurrentAction("I have arrived. Waiting 10 seconds...");

              if (queueDelayTimerRef.current !== null) {
                clearTimeout(queueDelayTimerRef.current);
              }

              queueDelayTimerRef.current = setTimeout(() => {
                console.log(
                  "QUEUE: 10-second wait finished. Processing next command."
                );

                queueDelayTimerRef.current = null;
                processNextCommand();
              }, 10000);

            } else if (status.status === "failed") {
              console.log(
                "QUEUE: Command failed. Processing next command immediately."
              );

              if (queueDelayTimerRef.current !== null) {
                clearTimeout(queueDelayTimerRef.current);
                queueDelayTimerRef.current = null;
              }

              processNextCommand();
            }

            if (Array.isArray(status.queue)) {
              // Queue is managed by this panel.
            }

            if (typeof status.error === "string") {
              setStatusError(status.error);
            }
          } catch (error) {
            console.error("Invalid robot status:", error);
          }
        }





        if (message.topic === "/robot_response") {
          const data = message.message as { data?: string };
          const response = data.data ?? "";

          setRobotResponse(response);

          if (
            response.toLowerCase().includes("which target do you mean")
          ) {
            activeCommandRef.current = null;
          }
        }
      }

      done();
    };

    return () => {
      context.onRender = undefined;
    };
  }, [context]);

  const startVoiceCommand = async () => {
    if (isRecording) {
      return;
    }

    setVoiceError("");
    setIsRecording(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(
          audioChunksRef.current,
          {
            type: mediaRecorder.mimeType,
          }
        );

        try {
          const response = await fetch(
            "http://127.0.0.1:8766/transcribe",
            {
              method: "POST",
              headers: {
                "Content-Type": "audio/wav",
              },
              body: audioBlob,
            }
          );

          if (!response.ok) {
            throw new Error(
              `Whisper server error: ${response.status}`
            );
          }

          const result = await response.json();

          if (result.error) {
            throw new Error(result.error);
          }

          const text = result.text?.trim();

          if (text) {
            setCommand(text);

          }
        } catch (error) {
          console.error(
            "Whisper transcription failed:",
            error
          );

          setVoiceError(
            error instanceof Error
              ? error.message
              : String(error)
          );
        }
      };

      mediaRecorder.start();

      setTimeout(() => {
        if (mediaRecorder.state === "recording") {
          mediaRecorder.stop();
        }
      }, 5000);

    } catch (error) {
      console.error(
        "Microphone access failed:",
        error
      );

      setIsRecording(false);

      setVoiceError(
        error instanceof Error
          ? error.message
          : String(error)
      );
    }
  };

  const stopNavigation = () => {
    if (!context.publish) {
      console.error("Foxglove publishing is not available.");
      return;
    }

    if (queueDelayTimerRef.current !== null) {
      clearTimeout(queueDelayTimerRef.current);
      queueDelayTimerRef.current = null;
    }

    context.publish?.("/stop_navigation", {});

    activeCommandRef.current = null;
    commandQueueRef.current = [];
    setQueue([]);
    setCurrentAction("I stopped.");
  };

  const sendCommand = () => {
    const trimmedCommand = command.trim();

    if (!trimmedCommand) {
      return;
    }

    if (!context.publish) {
      console.error(
        "Foxglove publishing is not available."
      );
      return;
    }

    console.log(
      "SEND COMMAND:",
      {
        command: trimmedCommand,
        activeCommand: activeCommandRef.current,
        queue: commandQueueRef.current,
      }
    );

    if (!activeCommandRef.current) {
      activeCommandRef.current = trimmedCommand;

      context.publish?.("/user_command", {
        data: trimmedCommand,
      });

      setCommand("");
      return;
    }

    commandQueueRef.current.push(trimmedCommand);
    setQueue([...commandQueueRef.current]);

    setCommand("");
  };

  const removeQueuedCommand = (index: number) => {
    commandQueueRef.current.splice(index, 1);
    setQueue([...commandQueueRef.current]);
  };

  const startMapping = async () => {
    if (!context.callService) {
      setEnvironmentMessage("Foxglove service calls are not available.");
      return;
    }

    setEnvironmentMessage("Starting new mapping session...");

    try {
      const result = await context.callService(
        "/start_mapping",
        {},
      ) as { success?: boolean; message?: string };

      if (result.success) {
        setIsMapping(true);
        setCurrentAction("Creating new environment...");
        setEnvironmentMessage(
          result.message || "New mapping session started.",
        );
        setShowEnvironmentModal(false);
      } else {
        setEnvironmentMessage(
          result.message || "Failed to start mapping.",
        );
      }
    } catch (error) {
      console.error("Failed to start mapping:", error);
      setEnvironmentMessage(
        error instanceof Error
          ? error.message
          : String(error),
      );
    }
  };


  return (
    <div
      style={{
        height: "100%",
        boxSizing: "border-box",
        padding: "18px",
        fontFamily: "Arial, sans-serif",
        overflowY: "auto",
      }}
    >

      {/* Header */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            fontSize: "22px",
            fontWeight: 700,
            marginBottom: "4px",
          }}
        >
          🤖 Robot Command Center
        </div>

        <div
          style={{
            fontSize: "13px",
            opacity: 0.65,
          }}
        >
          Give your robot a command using natural language.
        </div>
      </div>

      {/* Current Environment */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            fontSize: "15px",
            fontWeight: 600,
            marginBottom: "8px",
          }}
        >
          🌍 Current Environment
        </div>

        <div
          style={{
            padding: "12px",
            borderRadius: "9px",
            border: "1px solid rgba(128,128,128,0.25)",
            background: "rgba(128,128,128,0.05)",
            fontSize: "14px",
            fontWeight: 600,
          }}
        >
          {isMapping ? "Creating new environment..." : currentEnvironment}
        </div>

        {!isMapping ? (
          <button
            onClick={startMapping}
            style={{
              width: "100%",
              marginTop: "8px",
              padding: "10px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            ➕ CREATE NEW ENVIRONMENT
          </button>
        ) : (
          <button
            onClick={finishMapping}
            style={{
              width: "100%",
              marginTop: "8px",
              padding: "10px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            🛑 FINISH MAPPING
          </button>
        )}
        <button
          onClick={() => {
            setEnvironmentMessage("");
            setSelectedEnvironment(currentEnvironment);
            listEnvironments();
            setShowChangeEnvironmentModal(true);
          }}
          style={{
            width: "100%",
            marginTop: "8px",
            padding: "10px",
            borderRadius: "8px",
            border: "none",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          🔄 CHANGE ENVIRONMENT

        </button>

        {environmentMessage && (
          <div
            style={{
              marginTop: "8px",
              fontSize: "12px",
              opacity: 0.75,
              wordBreak: "break-word",
            }}
          >
            {environmentMessage}
          </div>
        )}
      </div>

      {/* Live Status */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "8px",
          }}
        >
          <div
            style={{
              fontSize: "15px",
              fontWeight: 700,
            }}
          >
            📡 Live Status
          </div>

          <div
            style={{
              fontSize: "11px",
              padding: "4px 8px",
              borderRadius: "10px",
              background: "rgba(80,180,100,0.12)",
              opacity: 0.8,
            }}
          >
            ● LIVE
          </div>
        </div>

        <div
          style={{
            padding: "14px",
            borderRadius: "10px",
            border: "1px solid rgba(128,128,128,0.25)",
            background: "rgba(128,128,128,0.05)",
          }}
        >
          {/* Current Action */}
          <div
            style={{
              paddingBottom: "12px",
              marginBottom: "12px",
              borderBottom: "1px solid rgba(128,128,128,0.18)",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                fontWeight: 600,
                letterSpacing: "0.7px",
                opacity: 0.5,
                marginBottom: "5px",
              }}
            >
              CURRENT ACTION
            </div>

            <div
              style={{
                fontSize: "14px",
                fontWeight: 600,
                wordBreak: "break-word",
              }}
            >
              {currentAction}
            </div>
          </div>

          {/* Queue */}
          <div
            style={{
              paddingBottom: "12px",
              marginBottom: "12px",
              borderBottom: "1px solid rgba(128,128,128,0.18)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "7px",
              }}
            >
              <div
                style={{
                  fontSize: "10px",
                  fontWeight: 600,
                  letterSpacing: "0.7px",
                  opacity: 0.5,
                }}
              >
                QUEUE
              </div>

              <div
                style={{
                  fontSize: "11px",
                  opacity: 0.55,
                }}
              >
                {queue.length} pending
              </div>
            </div>

            {queue.length > 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                {queue.map((item, index) => (
                  <div
                    key={`${item}-${index}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "9px",
                      padding: "8px",
                      borderRadius: "7px",
                      background: "rgba(128,128,128,0.08)",
                      fontSize: "12px",
                    }}
                  >
                    <div
                      style={{
                        width: "20px",
                        height: "20px",
                        minWidth: "20px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: "50%",
                        background: "rgba(128,128,128,0.15)",
                        fontSize: "10px",
                        fontWeight: 700,
                      }}
                    >
                      {index + 1}
                    </div>

                    <div
                      style={{
                        flex: 1,
                        wordBreak: "break-word",
                      }}
                    >
                      {item}
                    </div>

                    <button
                      onClick={() => removeQueuedCommand(index)}
                      title="Remove from queue"
                      style={{
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        fontSize: "13px",
                        padding: "3px 5px",
                        opacity: 0.55,
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div
                style={{
                  padding: "8px",
                  borderRadius: "7px",
                  background: "rgba(128,128,128,0.06)",
                  textAlign: "center",
                  fontSize: "12px",
                  opacity: 0.5,
                }}
              >
                Queue is empty
              </div>
            )}
          </div>

          {/* Map Tools */}
          <div
            style={{
              marginTop: "14px",
              marginBottom: "14px",
              padding: "12px",
              borderRadius: "9px",
              border: "1px solid rgba(128,128,128,0.25)",
              background: "rgba(128,128,128,0.05)",
            }}
          >
            <div
              style={{
                fontSize: "15px",
                fontWeight: 600,
                marginBottom: "10px",
              }}
            >
              🗺️ MAP TOOLS
            </div>

            <button
              onClick={() => {
                const nextTool =
                  mapTool === "semantic" ? "none" : "semantic";

                setMapTool(nextTool);

                context.publish?.("/interaction_mode", {
                  data: nextTool,
                });
              }}
              style={{
                width: "100%",
                padding: "9px",
                marginBottom: "7px",
                border: "none",
                borderRadius: "7px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: 600,
                background:
                  mapTool === "semantic"
                    ? "rgba(70,130,180,0.25)"
                    : "rgba(128,128,128,0.10)",
              }}
            >
              🗺️ Create Semantic Map
            </button>

            <button
              onClick={() => {
                const nextTool =
                  mapTool === "initial_pose" ? "none" : "initial_pose";

                setMapTool(nextTool);

                context.publish?.("/interaction_mode", {
                  data: nextTool,
                });
              }}
              style={{
                width: "100%",
                padding: "9px",
                marginBottom: "7px",
                border: "none",
                borderRadius: "7px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: 600,
                background:
                  mapTool === "initial_pose"
                    ? "rgba(70,130,180,0.25)"
                    : "rgba(128,128,128,0.10)",
              }}
            >
              🤖 Set Initial Robot Pose
            </button>

            <button
              onClick={() => {
                const nextTool =
                  mapTool === "navigation_goal"
                    ? "none"
                    : "navigation_goal";

                setMapTool(nextTool);

                context.publish?.("/interaction_mode", {
                  data: nextTool,
                });
              }}
              style={{
                width: "100%",
                padding: "9px",
                border: "none",
                borderRadius: "7px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: 600,
                background: "rgba(128,128,128,0.10)",
              }}
            >
              🎯 Set Navigation Goal
            </button>
          </div>

          {/* Navigation Goal */}
  {mapTool === "navigation_goal" && (
    <div
      style={{
        marginTop: 10,
        padding: 12,
        borderRadius: 8,
        background: "#1f2937",
        border: "1px solid #374151",
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          marginBottom: 6,
        }}
      >
        🎯 Navigation Goal
      </div>

      <div
        style={{
          fontSize: 12,
          color: "#9ca3af",
          marginBottom: 10,
        }}
      >
        Select the destination point on the map.
      </div>

      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        Step 1 / 1 — 📍 Destination
      </div>

      <div
        style={{
          fontSize: 11,
          color: "#9ca3af",
          marginTop: 4,
        }}
      >
        Click once on the map to send the robot to that location.
      </div>

      {clickedX !== null && clickedY !== null && (
        <div
          style={{
            marginTop: 10,
            fontSize: 11,
            color: "#d1d5db",
          }}
        >
          Selected: ({clickedX.toFixed(3)}, {clickedY.toFixed(3)})
        </div>
      )}
    </div>
  )}

  {/* Initial Robot Pose */}
          {mapTool === "initial_pose" && (
            <div
              style={{
                marginTop: "14px",
                marginBottom: "14px",
                padding: "12px",
                borderRadius: "9px",
                border: "1px solid rgba(70,130,180,0.35)",
                background: "rgba(70,130,180,0.08)",
              }}
            >
              <div
                style={{
                  fontSize: "15px",
                  fontWeight: 600,
                  marginBottom: "10px",
                }}
              >
                🤖 Initial Robot Pose
              </div>

              <div
                style={{
                  fontSize: "12px",
                  marginBottom: "10px",
                  opacity: 0.75,
                }}
              >
                Set the robot's starting position and heading on the map.
              </div>

              <div
                style={{
                  padding: "9px",
                  borderRadius: "7px",
                  background:
                    initialPoseStep === 1
                      ? "rgba(70,130,180,0.18)"
                      : "rgba(128,128,128,0.08)",
                  marginBottom: "7px",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "12px" }}>
                  Step 1 / 2 — 📍 Robot Position
                </div>
                <div
                  style={{
                    fontSize: "11px",
                    marginTop: "4px",
                    opacity: 0.7,
                  }}
                >
                  {initialPoseStep === 1
                    ? "Click the robot's position on the map."
                    : initialPoseFirstPoint
                      ? `Position selected: (${initialPoseFirstPoint.x.toFixed(3)}, ${initialPoseFirstPoint.y.toFixed(3)})`
                      : "Position selected."}
                </div>
              </div>

              <div
                style={{
                  padding: "9px",
                  borderRadius: "7px",
                  background:
                    initialPoseStep === 2
                      ? "rgba(70,130,180,0.18)"
                      : "rgba(128,128,128,0.08)",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "12px" }}>
                  Step 2 / 2 — 🧭 Robot Heading
                </div>
                <div
                  style={{
                    fontSize: "11px",
                    marginTop: "4px",
                    opacity: 0.7,
                  }}
                >
                  {initialPoseStep === 2
                    ? "Click in the direction the robot is facing."
                    : "Waiting for the robot position."}
                </div>
              </div>
            </div>
          )}

          {/* Semantic Object */}
          {mapTool === "semantic" && (
          <div
            style={{
              marginTop: "14px",
              marginBottom: "14px",
              padding: "12px",
              borderRadius: "9px",
              border: "1px solid rgba(128,128,128,0.25)",
              background: "rgba(128,128,128,0.05)",
            }}
          >
            <div
              style={{
                fontSize: "15px",
                fontWeight: 600,
                marginBottom: "10px",
              }}
            >
              📍 Semantic Object
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "10px",
                    opacity: 0.5,
                    marginBottom: "3px",
                  }}
                >
                  X
                </div>
                <div style={{ fontSize: "13px" }}>
                  {clickedX !== null ? clickedX.toFixed(3) : "—"}
                </div>
              </div>

              <div>
                <div
                  style={{
                    fontSize: "10px",
                    opacity: 0.5,
                    marginBottom: "3px",
                  }}
                >
                  Y
                </div>
                <div style={{ fontSize: "13px" }}>
                  {clickedY !== null ? clickedY.toFixed(3) : "—"}
                </div>
              </div>
            </div>

            <div style={{ marginTop: "12px" }}>
              <div
                style={{
                  fontSize: "10px",
                  opacity: 0.5,
                  marginBottom: "4px",
                }}
              >
                NAME
              </div>

              <input
                type="text"
                value={objectName}
                onChange={(event) =>
                  setObjectName(event.target.value)
                }
                placeholder="e.g. dolap"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "8px",
                  borderRadius: "7px",
                  border: "1px solid rgba(128,128,128,0.35)",
                  background: "transparent",
                  fontSize: "13px",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div style={{ marginTop: "10px" }}>
              <div
                style={{
                  fontSize: "10px",
                  opacity: 0.5,
                  marginBottom: "4px",
                }}
              >
                TYPE
              </div>

              <input
                type="text"
                value={objectType}
                onChange={(event) =>
                  setObjectType(event.target.value)
                }
                placeholder="e.g. furniture"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "8px",
                  borderRadius: "7px",
                  border: "1px solid rgba(128,128,128,0.35)",
                  background: "transparent",
                  fontSize: "13px",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <button
              onClick={saveSemanticObject}
              disabled={
                clickedX === null ||
                clickedY === null ||
                !objectName.trim() || !objectType.trim()
              }
              style={{
                width: "100%",
                marginTop: "12px",
                padding: "9px",
                border: "none",
                borderRadius: "7px",
                cursor:
                  clickedX !== null &&
                  clickedY !== null &&
                  objectName.trim()
                    ? "pointer"
                    : "not-allowed",
                fontSize: "13px",
                fontWeight: 600,
              }}
            >
              💾 Save Object
            </button>
          </div>

          )}

          {/* Error / Battery */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "8px",
            }}
          >
            <div
              style={{
                padding: "9px",
                borderRadius: "7px",
                background: "rgba(128,128,128,0.07)",
              }}
            >
              <div
                style={{
                  fontSize: "10px",
                  opacity: 0.5,
                  marginBottom: "3px",
                }}
              >
                ERROR
              </div>

              <div
                style={{
                  fontSize: "12px",
                  wordBreak: "break-word",
                }}
              >
                {statusError || "None"}
              </div>
            </div>

            <div
              style={{
                padding: "9px",
                borderRadius: "7px",
                background: "rgba(128,128,128,0.07)",
              }}
            >
              <div
                style={{
                  fontSize: "10px",
                  opacity: 0.5,
                  marginBottom: "3px",
                }}
              >
                BATTERY
              </div>

              <div style={{ fontSize: "12px" }}>
                N/A
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Command */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            fontSize: "15px",
            fontWeight: 600,
            marginBottom: "8px",
          }}
        >
          💬 Command
        </div>

        <textarea
          value={command}
          onChange={(event) =>
            setCommand(event.target.value)
          }
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey
            ) {
              event.preventDefault();
              sendCommand();
            }
          }}
          placeholder="Tell the robot what to do..."
          rows={4}
          style={{
            width: "100%",
            boxSizing: "border-box",
            resize: "vertical",
            padding: "12px",
            borderRadius: "9px",
            border:
              "1px solid rgba(128,128,128,0.4)",
            background: "transparent",
            fontSize: "14px",
            fontFamily: "inherit",
            outline: "none",
          }}
        />

        {voiceError && (
          <div
            style={{
              marginTop: "8px",
              fontSize: "12px",
              color: "red",
            }}
          >
            Microphone error: {voiceError}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: "8px",
            marginTop: "8px",
          }}
        >
          <button
            onClick={startVoiceCommand}
            disabled={isRecording}
            style={{
              padding: "10px 14px",
              borderRadius: "8px",
              border:
                "1px solid rgba(128,128,128,0.35)",
              background: "transparent",
              cursor: isRecording
                ? "default"
                : "pointer",
              fontSize: "13px",
              opacity: isRecording ? 0.6 : 1,
            }}
          >
            {isRecording
              ? "🎙️ Listening..."
              : "🎤 Voice"}
          </button>

          <button
            onClick={stopNavigation}
            style={{
              padding: "10px 14px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            ⛔ STOP
          </button>

          <button
            onClick={sendCommand}
            disabled={!command.trim()}
            style={{
              flex: 1,
              padding: "10px",
              borderRadius: "8px",
              border: "none",
              cursor: command.trim()
                ? "pointer"
                : "default",
              fontSize: "13px",
              fontWeight: 600,
              opacity: command.trim() ? 1 : 0.5,
            }}
          >
            ➤ Send Command
          </button>
        </div>
      </div>

          {/* Robot Response */}
          <div style={{ marginBottom: "18px" }}>
            <div
              style={{
                fontSize: "14px",
                fontWeight: 600,
                marginBottom: "8px",
              }}
            >
              🤖 Robot Response
            </div>

            <div
              style={{
                padding: "12px",
                borderRadius: "8px",
                border: "1px solid rgba(128,128,128,0.25)",
                minHeight: "18px",
                fontSize: "13px",
                opacity: robotResponse ? 1 : 0.5,
                wordBreak: "break-word",
              }}
            >
              <div>{robotResponse}</div>

              {robotResponse &&
                robotResponse !== "Waiting for response..." && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      marginTop: "10px",
                    }}
                  >
                    <button
                      onClick={() => {
                        setReply("");
                        setShowReplyModal(true);
                      }}
                      style={{
                        padding: "6px 12px",
                        borderRadius: "7px",
                        border: "none",
                        cursor: "pointer",
                        fontSize: "12px",
                        fontWeight: 600,
                      }}
                    >
                      ↩ Reply
                    </button>
                  </div>
                )}
            </div>
          </div>


      {/* Save Environment Modal */}
      {showChangeEnvironmentModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "430px",
              background: "var(--panel-background, white)",
              borderRadius: "12px",
              padding: "20px",
              boxSizing: "border-box",
              boxShadow: "0 8px 30px rgba(0, 0, 0, 0.25)",
            }}
          >
            <div
              style={{
                fontSize: "16px",
                fontWeight: 600,
                marginBottom: "14px",
              }}
            >
              🔄 Change Environment
            </div>

            <div
              style={{
                fontSize: "13px",
                marginBottom: "10px",
                opacity: 0.75,
              }}
            >
              Select a saved environment.
            </div>

            {availableEnvironments.length === 0 ? (
              <div
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  background: "rgba(128,128,128,0.08)",
                  fontSize: "13px",
                  opacity: 0.75,
                  marginBottom: "14px",
                }}
              >
                {environmentMessage || "No saved environments found."}
              </div>
            ) : (
              <div
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  border: "1px solid rgba(128,128,128,0.4)",
                  borderRadius: "8px",
                  overflow: "hidden",
                  marginBottom: "14px",
                }}
              >
                {availableEnvironments.map((environment) => (
                  <div
                    key={environment}
                    onClick={() => setSelectedEnvironment(environment)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 12px",
                      cursor: "pointer",
                      background:
                        selectedEnvironment === environment
                          ? "rgba(128,128,128,0.15)"
                          : "transparent",
                      borderBottom:
                        environment === availableEnvironments[availableEnvironments.length - 1]
                          ? "none"
                          : "1px solid rgba(128,128,128,0.2)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "13px",
                        fontWeight:
                          selectedEnvironment === environment ? 600 : 400,
                      }}
                    >
                      {environment}
                    </span>

                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        deleteEnvironment(environment);
                      }}
                      style={{
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        fontSize: "15px",
                        padding: "2px 4px",
                      }}
                      title={`Delete ${environment}`}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "8px",
              }}
            >
              <button
                onClick={() => {
                  setShowChangeEnvironmentModal(false);
                  setEnvironmentMessage("");
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: "7px",
                  border: "1px solid rgba(128,128,128,0.35)",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                Cancel
              </button>

              <button
                onClick={selectEnvironment}
                disabled={!selectedEnvironment.trim()}
                style={{
                  padding: "8px 14px",
                  borderRadius: "7px",
                  border: "none",
                  cursor: selectedEnvironment.trim()
                    ? "pointer"
                    : "default",
                  fontSize: "12px",
                  fontWeight: 600,
                  opacity: selectedEnvironment.trim() ? 1 : 0.5,
                }}
              >
                🔄 Change Environment
              </button>
            </div>
          </div>
        </div>
      )}


      {showEnvironmentModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "430px",
              background: "var(--panel-background, white)",
              borderRadius: "12px",
              padding: "20px",
              boxSizing: "border-box",
              boxShadow: "0 8px 30px rgba(0, 0, 0, 0.25)",
            }}
          >
            <div
              style={{
                fontSize: "16px",
                fontWeight: 600,
                marginBottom: "14px",
              }}
            >
              💾 Save Environment
            </div>

            <div
              style={{
                fontSize: "13px",
                marginBottom: "8px",
                opacity: 0.75,
              }}
            >
              Enter a name to save the mapped environment.
            </div>

            <input
              type="text"
              value={newEnvironmentName}
              onChange={(event) =>
                setNewEnvironmentName(event.target.value)
              }
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  newEnvironmentName.trim()
                ) {
                  event.preventDefault();
                  saveEnvironment();
                }
              }}
              placeholder="e.g. living_room"
              autoFocus
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px",
                borderRadius: "8px",
                border: "1px solid rgba(128,128,128,0.4)",
                background: "transparent",
                fontSize: "13px",
                fontFamily: "inherit",
                outline: "none",
                marginBottom: "14px",
              }}
            />

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "8px",
              }}
            >
              <button
                onClick={() => {
                  setShowEnvironmentModal(false);
                  setNewEnvironmentName("");
                  setEnvironmentMessage("");
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: "7px",
                  border: "1px solid rgba(128,128,128,0.35)",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                Cancel
              </button>

              <button
                onClick={saveEnvironment}
                disabled={!newEnvironmentName.trim()}
                style={{
                  padding: "8px 14px",
                  borderRadius: "7px",
                  border: "none",
                  cursor: newEnvironmentName.trim()
                    ? "pointer"
                    : "default",
                  fontSize: "12px",
                  fontWeight: 600,
                  opacity: newEnvironmentName.trim() ? 1 : 0.5,
                }}
              >
                💾 Save Environment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reply Modal */}
      {showReplyModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "430px",
              background: "var(--panel-background, white)",
              borderRadius: "12px",
              padding: "20px",
              boxSizing: "border-box",
              boxShadow: "0 8px 30px rgba(0, 0, 0, 0.25)",
            }}
          >
            <div
              style={{
                fontSize: "16px",
                fontWeight: 600,
                marginBottom: "14px",
              }}
            >
              ↩ Reply to Robot
            </div>

            <div
              style={{
                fontSize: "13px",
                marginBottom: "12px",
                opacity: 0.8,
              }}
            >
              {robotResponse}
            </div>

            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="Type your answer..."
              rows={3}
              autoFocus
              style={{
                width: "100%",
                boxSizing: "border-box",
                resize: "vertical",
                padding: "10px",
                borderRadius: "8px",
                border:
                  "1px solid rgba(128,128,128,0.4)",
                background: "transparent",
                fontSize: "13px",
                fontFamily: "inherit",
                outline: "none",
                marginBottom: "12px",
              }}
            />

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "8px",
              }}
            >
              <button
                onClick={() => {
                  setShowReplyModal(false);
                  setReply("");
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: "7px",
                  border:
                    "1px solid rgba(128,128,128,0.35)",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                Cancel
              </button>

              <button
                onClick={() => {
                  const trimmedReply = reply.trim();

                  if (!trimmedReply || !context.publish) {
                    return;
                  }

                  activeCommandRef.current = trimmedReply;

                  context.publish("/user_command", {
                    data: trimmedReply,
                  });

                  setReply("");
                  setShowReplyModal(false);
                }}
                disabled={!reply.trim()}
                style={{
                  padding: "8px 14px",
                  borderRadius: "7px",
                  border: "none",
                  cursor: reply.trim()
                    ? "pointer"
                    : "default",
                  fontSize: "12px",
                  fontWeight: 600,
                  opacity: reply.trim() ? 1 : 0.5,
                }}
              >
                Send Reply
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export function initExamplePanel(
  context: PanelExtensionContext,
): () => void {
  context.advertise?.(
    "/user_command",
    "std_msgs/String",
  );

  const root = createRoot(
    context.panelElement
  );

  root.render(
    <ExamplePanel context={context} />
  );

  return () => {
    root.unmount();
  };
}
