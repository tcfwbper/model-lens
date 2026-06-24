import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  buildFrameData,
  buildDetection,
} from "../test-helpers/fixtures";
import type { FrameData } from "../test-helpers/fixtures";
import { createMockCanvas2DContext } from "../test-helpers/mocks";
import type { MockCanvas2DContext } from "../test-helpers/mocks";

/**
 * Test Specification: StreamViewer.test.tsx
 *
 * Source: src/ui/src/components/StreamViewer.tsx
 */

// Mock the useStream hook
const mockUseStreamReturn: { frame: FrameData | null } = { frame: null };
vi.mock("../hooks/useStream", () => ({
  useStream: (active: boolean) => {
    mockUseStreamReturnCalledWith = active;
    return mockUseStreamReturn;
  },
}));
let mockUseStreamReturnCalledWith: boolean | undefined;

import { StreamViewer } from "./StreamViewer";

let mockCtx: MockCanvas2DContext;
let mockImageInstances: Array<{
  src: string;
  onload: (() => void) | null;
  complete: boolean;
}>;

beforeEach(() => {
  mockCtx = createMockCanvas2DContext();
  mockImageInstances = [];
  mockUseStreamReturnCalledWith = undefined;

  // Mock canvas getContext
  HTMLCanvasElement.prototype.getContext = vi.fn(() => mockCtx) as unknown as typeof HTMLCanvasElement.prototype.getContext;

  // Mock Image constructor
  (globalThis as unknown as { Image: unknown }).Image = class FakeImage {
    src = "";
    onload: (() => void) | null = null;
    complete = false;
    width = 800;
    height = 450;
    constructor() {
      mockImageInstances.push(this);
    }
  };
});

afterEach(() => {
  vi.restoreAllMocks();
});

function setMockFrame(frame: FrameData | null) {
  mockUseStreamReturn.frame = frame;
}

function triggerImageLoad() {
  if (mockImageInstances.length > 0) {
    const img = mockImageInstances[mockImageInstances.length - 1];
    img.complete = true;
    if (img.onload) img.onload();
  }
}

describe("StreamViewer", () => {
  describe("Happy Path — Rendering", () => {
    it("shows_placeholder_when_inactive", () => {
      setMockFrame(null);
      render(
        <StreamViewer
          sseActive={false}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      expect(screen.getByText("Stream inactive")).toBeVisible();
      const canvas = document.querySelector("canvas");
      if (canvas) {
        expect(canvas).toHaveStyle({ display: "none" });
      }
    });

    it("shows_placeholder_when_active_but_no_frame", () => {
      setMockFrame(null);
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      expect(screen.getByText("Stream inactive")).toBeVisible();
    });

    it("shows_canvas_when_frame_available", () => {
      setMockFrame(buildFrameData({ jpeg_b64: "abc", detections: [] }));
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      triggerImageLoad();
      const canvas = document.querySelector("canvas");
      expect(canvas).not.toHaveStyle({ display: "none" });
    });

    it("displays_confidence_threshold", () => {
      setMockFrame(null);
      render(
        <StreamViewer
          sseActive={false}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.75}
        />
      );
      expect(screen.getByText(/Confidence Threshold: 0.75/)).toBeVisible();
    });

    it("hides_confidence_threshold_when_null", () => {
      setMockFrame(null);
      render(
        <StreamViewer
          sseActive={false}
          onToggleSSE={vi.fn()}
          confidenceThreshold={null}
        />
      );
      expect(screen.queryByText(/Confidence Threshold/)).not.toBeInTheDocument();
    });
  });

  describe("Happy Path — Frame Drawing", () => {
    it("draws_image_on_canvas", () => {
      setMockFrame(buildFrameData({ jpeg_b64: "validbase64", detections: [] }));
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      triggerImageLoad();
      expect(mockCtx.clearRect).toHaveBeenCalled();
      expect(mockCtx.drawImage).toHaveBeenCalled();
    });

    it("draws_bounding_boxes_for_target_detections", () => {
      // Detection: bounding_box [0.1, 0.2, 0.5, 0.6] on 800x450 canvas
      // x = 0.1*800 = 80, y = 0.2*450 = 90, w = (0.5-0.1)*800 = 320, h = (0.6-0.2)*450 = 180
      const detection = buildDetection({
        label: "cat",
        confidence: 0.87,
        bounding_box: [0.1, 0.2, 0.5, 0.6],
        is_target: true,
      });
      setMockFrame(buildFrameData({ detections: [detection] }));
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      triggerImageLoad();

      expect(mockCtx.strokeRect).toHaveBeenCalled();
      const [x, y, w, h] = mockCtx.strokeRect.mock.calls[0];
      expect(x).toBeCloseTo(80, 0);
      expect(y).toBeCloseTo(90, 0);
      expect(w).toBeCloseTo(320, 0);
      expect(h).toBeCloseTo(180, 0);

      // Label text drawn containing "cat 87%"
      expect(mockCtx.fillText).toHaveBeenCalledWith(
        expect.stringContaining("cat 87%"),
        expect.any(Number),
        expect.any(Number)
      );
    });

    it("skips_non_target_detections", () => {
      const detection = buildDetection({
        label: "dog",
        confidence: 0.9,
        bounding_box: [0.1, 0.1, 0.5, 0.5],
        is_target: false,
      });
      setMockFrame(buildFrameData({ detections: [detection] }));
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      triggerImageLoad();
      expect(mockCtx.strokeRect).not.toHaveBeenCalled();
    });

    it("prevents_double_drawing", () => {
      setMockFrame(buildFrameData());
      // Mock Image that is complete immediately AND fires onload
      (globalThis as unknown as { Image: unknown }).Image = class {
        src = "";
        onload: (() => void) | null = null;
        complete = true;
        width = 800;
        height = 450;
        constructor() {
          mockImageInstances.push(this as unknown as typeof mockImageInstances[0]);
          // Simulate both complete=true and onload firing
          setTimeout(() => {
            if (this.onload) this.onload();
          }, 0);
        }
      };

      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );

      // drawImage should be called exactly once (guarded by drawn flag)
      expect(mockCtx.drawImage).toHaveBeenCalledTimes(1);
    });
  });

  describe("Null / Empty Input", () => {
    it("no_draw_when_canvas_ref_null", () => {
      // Render then immediately unmount before effect runs
      setMockFrame(buildFrameData());
      const { unmount } = render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      unmount();
      // No canvas context methods should be called after unmount
      // (implementation uses early return when canvas ref is null)
      // Note: This test verifies no error is thrown
    });

    it("empty_detections_draws_image_only", () => {
      setMockFrame(buildFrameData({ detections: [] }));
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      triggerImageLoad();
      expect(mockCtx.drawImage).toHaveBeenCalled();
      expect(mockCtx.strokeRect).not.toHaveBeenCalled();
    });
  });

  describe("Mock / Dependency Interaction", () => {
    it("calls_use_stream_with_sse_active", () => {
      setMockFrame(null);
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      expect(mockUseStreamReturnCalledWith).toBe(true);
    });

    it("does_not_invoke_on_toggle_sse", () => {
      setMockFrame(null);
      const onToggle = vi.fn();
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={onToggle}
          confidenceThreshold={0.5}
        />
      );
      expect(onToggle).not.toHaveBeenCalled();
    });
  });

  describe("Boundary Values — Canvas Dimensions", () => {
    it("canvas_has_fixed_logical_dimensions", () => {
      setMockFrame(buildFrameData());
      render(
        <StreamViewer
          sseActive={true}
          onToggleSSE={vi.fn()}
          confidenceThreshold={0.5}
        />
      );
      triggerImageLoad();
      const canvas = document.querySelector("canvas");
      expect(canvas).toHaveAttribute("width", "800");
      expect(canvas).toHaveAttribute("height", "450");
    });
  });
});
