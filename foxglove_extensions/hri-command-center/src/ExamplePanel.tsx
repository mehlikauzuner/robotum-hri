import { PanelExtensionContext } from "@foxglove/extension";
import { ReactElement, useState } from "react";
import { createRoot } from "react-dom/client";

interface Props {
  context: PanelExtensionContext;
}

function ExamplePanel({ context }: Props): ReactElement {
  const [command, setCommand] = useState("");
  const [lastCommand, setLastCommand] = useState("");

  const quickCommands = [
    { icon: "↑", label: "İleri" },
    { icon: "←", label: "Sola Dön" },
    { icon: "→", label: "Sağa Dön" },
    { icon: "↓", label: "Geri" },
    { icon: "■", label: "Dur" },
  ];

  const exampleCommands = [
    "Go to the kitchen",
    "Go to the table",
    "Move forward",
    "Turn left",
  ];

  const sendCommand = () => {
    const trimmedCommand = command.trim();

    if (!trimmedCommand) {
      return;
    }

    if (!context.publish) {
      console.error("Foxglove publishing is not available.");
      return;
    }

    context.publish("/user_command", {
      data: trimmedCommand,
    });

    setLastCommand(trimmedCommand);
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
      <div style={{ marginBottom: "16px" }}>
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

      {/* Robot Status */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 12px",
          marginBottom: "18px",
          borderRadius: "9px",
          border: "1px solid rgba(128,128,128,0.3)",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            opacity: 0.6,
            fontWeight: 600,
          }}
        >
          ROBOT STATUS
        </span>

        <span
          style={{
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          🟢 Ready
        </span>
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
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
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
            border: "1px solid rgba(128,128,128,0.4)",
            background: "transparent",
            fontSize: "14px",
            fontFamily: "inherit",
            outline: "none",
          }}
        />

        <div
          style={{
            display: "flex",
            gap: "8px",
            marginTop: "8px",
          }}
        >
          <button
            style={{
              padding: "10px 14px",
              borderRadius: "8px",
              border: "1px solid rgba(128,128,128,0.35)",
              background: "transparent",
              cursor: "pointer",
              fontSize: "13px",
            }}
          >
            🎤 Voice
          </button>

          <button
            onClick={sendCommand}
            disabled={!command.trim()}
            style={{
              flex: 1,
              padding: "10px",
              borderRadius: "8px",
              border: "none",
              cursor: command.trim() ? "pointer" : "default",
              fontSize: "13px",
              fontWeight: 600,
              opacity: command.trim() ? 1 : 0.5,
            }}
          >
            ➤ Send Command
          </button>
        </div>
      </div>

      {/* Quick Commands */}
      <div style={{ marginBottom: "18px" }}>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            marginBottom: "8px",
          }}
        >
          ⚡ Quick Commands
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: "6px",
          }}
        >
          {quickCommands.map((item) => (
            <button
              key={item.label}
              onClick={() => setCommand(item.label)}
              style={{
                padding: "9px 4px",
                borderRadius: "7px",
                border: "1px solid rgba(128,128,128,0.3)",
                background: "transparent",
                cursor: "pointer",
                fontSize: "11px",
              }}
            >
              <div style={{ fontSize: "15px" }}>{item.icon}</div>
              <div style={{ marginTop: "3px" }}>{item.label}</div>
            </button>
          ))}
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
            border: "1px solid rgba(128,128,128,0.25)",
            minHeight: "18px",
            fontSize: "13px",
            opacity: lastCommand ? 1 : 0.5,
          }}
        >
          {lastCommand || "No command sent yet."}
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
            border: "1px solid rgba(128,128,128,0.25)",
            fontFamily: "monospace",
            fontSize: "12px",
            opacity: 0.6,
          }}
        >
          {"{ action: waiting }"}
        </div>
      </div>

      {/* Examples */}
      <div>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            marginBottom: "8px",
          }}
        >
          💡 Examples
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "5px",
          }}
        >
          {exampleCommands.map((example) => (
            <button
              key={example}
              onClick={() => setCommand(example)}
              style={{
                padding: "8px 10px",
                borderRadius: "7px",
                border: "1px solid rgba(128,128,128,0.2)",
                background: "transparent",
                cursor: "pointer",
                textAlign: "left",
                fontSize: "12px",
              }}
            >
              "{example}"
            </button>
          ))}
        </div>
      </div>
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

  const root = createRoot(context.panelElement);

  root.render(<ExamplePanel context={context} />);

  return () => {
    root.unmount();
  };
}