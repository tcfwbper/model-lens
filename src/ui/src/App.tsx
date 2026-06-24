/**
 * Root React component for the ModelLens UI.
 * Orchestrates page layout, SSE toggle state, and distributes configuration
 * data and mutation callbacks to child components.
 */
import { useState } from "react";
import { useConfig } from "./hooks/useConfig";
import { Header } from "./components/Header";
import { CameraConfig } from "./components/CameraConfig";
import { StreamViewer } from "./components/StreamViewer";
import { TargetLabels } from "./components/TargetLabels";

export default function App(): JSX.Element {
  const { runtimeConfig, validLabels, updateCamera, updateLabels } = useConfig();
  const [sseActive, setSseActive] = useState(false);

  const camera = runtimeConfig?.camera ?? null;
  const activeLabels = runtimeConfig?.target_labels ?? [];
  const confidenceThreshold = runtimeConfig?.confidence_threshold ?? null;

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#F5F6F8",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <Header />
      <div style={{ padding: "16px 24px" }}>
        <CameraConfig camera={camera} onUpdate={updateCamera} />
        <div style={{ display: "flex", gap: "16px", marginTop: "16px" }}>
          <div style={{ flex: 2 }}>
            <StreamViewer
              sseActive={sseActive}
              onToggleSSE={setSseActive}
              confidenceThreshold={confidenceThreshold}
            />
          </div>
          <div style={{ flex: 1 }}>
            <TargetLabels
              validLabels={validLabels}
              activeLabels={activeLabels}
              onUpdate={updateLabels}
            />
            <div style={{ display: "flex", gap: "8px", marginTop: "16px" }}>
              <button
                style={{
                  flex: 1,
                  padding: "8px 16px",
                  backgroundColor: sseActive ? "#A8C4DC" : "#5B8CB8",
                  color: "#FFFFFF",
                  borderStyle: "none",
                  borderRadius: "4px",
                  cursor: sseActive ? "default" : "pointer",
                }}
                disabled={sseActive}
                onClick={() => setSseActive(true)}
              >
                Start Stream
              </button>
              <button
                style={{
                  flex: 1,
                  padding: "8px 16px",
                  backgroundColor: !sseActive ? "#D4DAE0" : "#6B7B8D",
                  color: "#FFFFFF",
                  borderStyle: "none",
                  borderRadius: "4px",
                  cursor: !sseActive ? "default" : "pointer",
                }}
                disabled={!sseActive}
                onClick={() => setSseActive(false)}
              >
                Stop Stream
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
