import { useState } from "react";
import Header from "./components/Header";
import CameraConfig from "./components/CameraConfig";
import TargetLabels from "./components/TargetLabels";
import StreamViewer from "./components/StreamViewer";
import { useConfig } from "./hooks/useConfig";
import type { CameraConfigData } from "./hooks/useConfig";

export default function App() {
  const { runtimeConfig, validLabels, updateCamera, updateLabels } =
    useConfig();
  const [sseActive, setSseActive] = useState(false);

  const camera = runtimeConfig?.camera ?? null;
  const activeLabels = runtimeConfig?.target_labels ?? [];
  const confidenceThreshold = runtimeConfig?.confidence_threshold ?? null;

  async function handleCameraUpdate(cameraData: CameraConfigData) {
    await updateCamera(cameraData);
  }

  async function handleLabelsUpdate(labels: string[]) {
    await updateLabels(labels);
  }

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
        <CameraConfig camera={camera} onUpdate={handleCameraUpdate} />

        <div
          style={{
            display: "flex",
            gap: "16px",
            marginTop: "16px",
          }}
        >
          <div style={{ flex: 2 }}>
            <StreamViewer
              sseActive={sseActive}
              onToggleSSE={setSseActive}
              confidenceThreshold={confidenceThreshold}
            />
          </div>

          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "16px" }}>
            <TargetLabels
              validLabels={validLabels}
              activeLabels={activeLabels}
              onUpdate={handleLabelsUpdate}
            />

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                disabled={sseActive}
                onClick={() => setSseActive(true)}
                style={{
                  flex: 1,
                  padding: "8px 16px",
                  backgroundColor: sseActive ? "#A8C4DC" : "#5B8CB8",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: "4px",
                  cursor: sseActive ? "default" : "pointer",
                }}
              >
                Start Stream
              </button>
              <button
                disabled={!sseActive}
                onClick={() => setSseActive(false)}
                style={{
                  flex: 1,
                  padding: "8px 16px",
                  backgroundColor: !sseActive ? "#D4DAE0" : "#6B7B8D",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: "4px",
                  cursor: !sseActive ? "default" : "pointer",
                }}
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
