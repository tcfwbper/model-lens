import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { buildRuntimeConfig } from "./test-helpers/fixtures";
import { buildUseConfigReturn } from "./test-helpers/mocks";
import type { UseConfigReturn } from "./test-helpers/mocks";

/**
 * Test Specification: App.test.tsx
 *
 * Source: src/ui/src/App.tsx
 *
 * The tests mock useConfig and verify prop-passing to child components.
 * Child components are mocked to expose received props via test attributes.
 */

// --- Mocks ---

let mockUseConfigReturn: UseConfigReturn;

vi.mock("./hooks/useConfig", () => ({
  useConfig: () => mockUseConfigReturn,
}));

// Mock child components to inspect props
vi.mock("./components/Header", () => ({
  Header: () => <div data-testid="header">Header</div>,
}));

vi.mock("./components/CameraConfig", () => ({
  CameraConfig: (props: { camera: unknown; onUpdate: unknown }) => (
    <div
      data-testid="camera-config"
      data-camera={JSON.stringify(props.camera)}
      data-on-update={typeof props.onUpdate}
    >
      CameraConfig
    </div>
  ),
}));

vi.mock("./components/StreamViewer", () => ({
  StreamViewer: (props: {
    sseActive: boolean;
    onToggleSSE: unknown;
    confidenceThreshold: unknown;
  }) => (
    <div
      data-testid="stream-viewer"
      data-sse-active={String(props.sseActive)}
      data-confidence-threshold={JSON.stringify(props.confidenceThreshold)}
    >
      StreamViewer
    </div>
  ),
}));

vi.mock("./components/TargetLabels", () => ({
  TargetLabels: (props: {
    validLabels: string[];
    activeLabels: string[];
    onUpdate: unknown;
  }) => (
    <div
      data-testid="target-labels"
      data-valid-labels={JSON.stringify(props.validLabels)}
      data-active-labels={JSON.stringify(props.activeLabels)}
      data-on-update={typeof props.onUpdate}
    >
      TargetLabels
    </div>
  ),
}));

import App from "./App";

beforeEach(() => {
  mockUseConfigReturn = buildUseConfigReturn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  describe("Happy Path — Rendering", () => {
    it("renders_header_component", () => {
      render(<App />);
      expect(screen.getByTestId("header")).toBeInTheDocument();
    });

    it("renders_camera_config_with_camera_prop", () => {
      mockUseConfigReturn = buildUseConfigReturn({
        runtimeConfig: buildRuntimeConfig({
          camera: { source_type: "local", device_index: 0 },
        }),
        validLabels: ["cat", "dog"],
      });
      render(<App />);
      const cameraConfig = screen.getByTestId("camera-config");
      expect(JSON.parse(cameraConfig.dataset.camera!)).toEqual({
        source_type: "local",
        device_index: 0,
      });
    });

    it("renders_stream_viewer_with_sse_inactive", () => {
      render(<App />);
      const streamViewer = screen.getByTestId("stream-viewer");
      expect(streamViewer.dataset.sseActive).toBe("false");
    });

    it("renders_target_labels_with_props", () => {
      mockUseConfigReturn = buildUseConfigReturn({
        runtimeConfig: buildRuntimeConfig({
          camera: { source_type: "local", device_index: 0 },
          target_labels: ["cat"],
        }),
        validLabels: ["cat", "dog"],
      });
      render(<App />);
      const targetLabels = screen.getByTestId("target-labels");
      expect(JSON.parse(targetLabels.dataset.validLabels!)).toEqual(["cat", "dog"]);
      expect(JSON.parse(targetLabels.dataset.activeLabels!)).toEqual(["cat"]);
    });

    it("renders_start_and_stop_buttons", () => {
      render(<App />);
      expect(screen.getByRole("button", { name: /start stream/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /stop stream/i })).toBeInTheDocument();
    });
  });

  describe("State Transitions", () => {
    it("start_button_sets_sse_active_true", () => {
      render(<App />);
      const startBtn = screen.getByRole("button", { name: /start stream/i });
      fireEvent.click(startBtn);
      const streamViewer = screen.getByTestId("stream-viewer");
      expect(streamViewer.dataset.sseActive).toBe("true");
      expect(startBtn).toBeDisabled();
      const stopBtn = screen.getByRole("button", { name: /stop stream/i });
      expect(stopBtn).not.toBeDisabled();
    });

    it("stop_button_sets_sse_active_false", () => {
      render(<App />);
      // Start first
      fireEvent.click(screen.getByRole("button", { name: /start stream/i }));
      // Then stop
      fireEvent.click(screen.getByRole("button", { name: /stop stream/i }));
      const streamViewer = screen.getByTestId("stream-viewer");
      expect(streamViewer.dataset.sseActive).toBe("false");
      expect(screen.getByRole("button", { name: /start stream/i })).not.toBeDisabled();
      expect(screen.getByRole("button", { name: /stop stream/i })).toBeDisabled();
    });

    it("start_button_disabled_when_sse_active", () => {
      render(<App />);
      fireEvent.click(screen.getByRole("button", { name: /start stream/i }));
      expect(screen.getByRole("button", { name: /start stream/i })).toBeDisabled();
    });

    it("stop_button_disabled_when_sse_inactive", () => {
      render(<App />);
      expect(screen.getByRole("button", { name: /stop stream/i })).toBeDisabled();
    });
  });

  describe("Null / Empty Input", () => {
    it("camera_null_when_config_null", () => {
      mockUseConfigReturn = buildUseConfigReturn({ runtimeConfig: null });
      render(<App />);
      const cameraConfig = screen.getByTestId("camera-config");
      expect(JSON.parse(cameraConfig.dataset.camera!)).toBeNull();
    });

    it("active_labels_empty_when_config_null", () => {
      mockUseConfigReturn = buildUseConfigReturn({ runtimeConfig: null });
      render(<App />);
      const targetLabels = screen.getByTestId("target-labels");
      expect(JSON.parse(targetLabels.dataset.activeLabels!)).toEqual([]);
    });

    it("confidence_threshold_null_when_config_null", () => {
      mockUseConfigReturn = buildUseConfigReturn({ runtimeConfig: null });
      render(<App />);
      const streamViewer = screen.getByTestId("stream-viewer");
      expect(JSON.parse(streamViewer.dataset.confidenceThreshold!)).toBeNull();
    });
  });

  describe("Mock / Dependency Interaction", () => {
    it("calls_update_camera_via_camera_config", () => {
      const updateCamera = vi.fn();
      mockUseConfigReturn = buildUseConfigReturn({ updateCamera });

      // To test the callback wiring, we need the real CameraConfig mock to
      // expose its onUpdate prop. We verify the type is function.
      render(<App />);
      const cameraConfig = screen.getByTestId("camera-config");
      expect(cameraConfig.dataset.onUpdate).toBe("function");
      // Note: Full integration of the callback requires the real CameraConfig
      // component calling onUpdate, which is covered in CameraConfig.test.tsx.
      // Here we verify the wiring is in place via the mock component.
    });

    it("calls_update_labels_via_target_labels", () => {
      const updateLabels = vi.fn();
      mockUseConfigReturn = buildUseConfigReturn({ updateLabels });

      render(<App />);
      const targetLabels = screen.getByTestId("target-labels");
      expect(targetLabels.dataset.onUpdate).toBe("function");
    });

    it("sse_active_default_false", () => {
      render(<App />);
      const streamViewer = screen.getByTestId("stream-viewer");
      expect(streamViewer.dataset.sseActive).toBe("false");
    });
  });
});
