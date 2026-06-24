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
    <div>
      <Header />
      <CameraConfig camera={camera} onUpdate={updateCamera} />
      <div style={{ display: "flex" }}>
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
          <button
            disabled={sseActive}
            onClick={() => setSseActive(true)}
          >
            Start Stream
          </button>
          <button
            disabled={!sseActive}
            onClick={() => setSseActive(false)}
          >
            Stop Stream
          </button>
        </div>
      </div>
    </div>
  );
}
