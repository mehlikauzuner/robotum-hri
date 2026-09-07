import { PanelExtensionContext } from "@foxglove/extension";
import { ReactElement, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

interface Props {
  context: PanelExtensionContext;
}

function ExamplePanel({ context }: Props): ReactElement {
  const [command, setCommand] = useState("");
  const [lastCommand, setLastCommand] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  const [currentAction, setCurrentAction] = useState("Idle");
  const [queue, setQueue] = useState<string[]>([]);
  const [statusError, setStatusError] = useState("");

  const [parsedAction, setParsedAction] = useState("{ action: waiting }");
  const [robotResponse, setRobotResponse] = useState("Waiting for response...");

  const [showReplyModal, setShowReplyModal] = useState(false);
  const [reply, setReply] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const commandQueueRef = useRef<string[]>([]);
  const activeCommandRef = useRef<string | null>(null);

  const processNextCommand = () => {
    if (!context.publish) {
      return;
    }

    const nextCommand = commandQueueRef.current.shift();

    setQueue([...commandQueueRef.current]);

    if (!nextCommand) {
      activeCommandRef.current = null;
      return;
    }

    activeCommandRef.current = nextCommand;

    context.publish("/user_command", {
      data: nextCommand,
    });

    setLastCommand(nextCommand);
  };

  useEffect(() => {
    context.advertise?.("/stop_navigation", "std_msgs/msg/Empty");

    context.subscribe([
      { topic: "/robot_status" },
      { topic: "/parsed_command" },
      { topic: "/robot_response" },
    ]);

    context.watch("currentFrame");

    context.onRender = (renderState, done) => {
      for (const message of renderState.currentFrame ?? []) {
        if (message.topic === "/robot_status") {
          const data = message.message as { data?: string };

          try {
            const status = JSON.parse(data.data ?? "{}");

            console.log("ROBOT STATUS RECEIVED:", status);

            if (typeof status.current_action === "string") {
              setCurrentAction(status.current_action);
            }

            // Queue progression is based on structured status,
            // not on the wording of the robot response.
            if (
              status.status === "completed" ||
              status.status === "failed"
            ) {
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

        if (message.topic === "/parsed_command") {
          const data = message.message as { data?: string };

          try {
            const parsed = JSON.parse(data.data ?? "{}");
            setParsedAction(JSON.stringify(parsed));
          } catch {
            setParsedAction(data.data ?? "{ invalid }");
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
            setLastCommand(text);
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

    context.publish("/stop_navigation", {});

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

    if (!activeCommandRef.current) {
      activeCommandRef.current = trimmedCommand;

      context.publish("/user_command", {
        data: trimmedCommand,
      });

      setLastCommand(trimmedCommand);
      setCommand("");
      return;
    }

    commandQueueRef.current.push(trimmedCommand);
    setQueue([...commandQueueRef.current]);
    setLastCommand(trimmedCommand);
    setCommand("");
  };

  const removeQueuedCommand = (index: number) => {
    commandQueueRef.current.splice(index, 1);
    setQueue([...commandQueueRef.current]);
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

      {/* Last Command */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            marginBottom: "8px",
          }}
        >
          📋 Last Command
        </div>

        <div
          style={{
            padding: "11px 12px",
            borderRadius: "8px",
            border:
              "1px solid rgba(128,128,128,0.25)",
            minHeight: "18px",
            fontSize: "13px",
            opacity: lastCommand ? 1 : 0.5,
          }}
        >
          {lastCommand ||
            "No command sent yet."}
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
            padding: "11px 12px",
            borderRadius: "8px",
            border:
              "1px solid rgba(128,128,128,0.25)",
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

      {/* Parsed Action */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            marginBottom: "8px",
          }}
        >
          🔎 Parsed Action
        </div>

        <div
          style={{
            padding: "12px",
            borderRadius: "8px",
            border:
              "1px solid rgba(128,128,128,0.25)",
            fontFamily: "monospace",
            fontSize: "12px",
            opacity: 0.8,
            wordBreak: "break-word",
          }}
        >
          {parsedAction}
        </div>
      </div>

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

                  setLastCommand(trimmedReply);
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
