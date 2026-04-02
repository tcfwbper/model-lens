import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from "vitest";
import StreamViewer from "../../../src/ui/src/components/StreamViewer";
import { useStream } from "../../../src/ui/src/hooks/useStream";

vi.mock("../../../src/ui/src/hooks/useStream");

const mockUseStream = useStream as Mock;

interface Detection {
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number];
  is_target: boolean;
}

interface FrameData {
  jpeg_b64: string;
  timestamp: number;
  source: string;
  detections: Detection[];
}

function createMockContext() {
  return {
    drawImage: vi.fn(),
    strokeRect: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    measureText: vi.fn(() => ({ width: 50 })),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    set strokeStyle(_v: string) {},
    set fillStyle(_v: string) {},
    set lineWidth(_v: number) {},
    set font(_v: string) {},
    canvas: { width: 800, height: 450 },
  };
}

describe("StreamViewer", () => {
  let mockCtx: ReturnType<typeof createMockContext>;

  const OriginalImage = globalThis.Image;

  beforeEach(() => {
    mockCtx = createMockContext();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      mockCtx as unknown as CanvasRenderingContext2D,
    );
    mockUseStream.mockReturnValue({ frame: null });

    // jsdom's Image doesn't fire onload for data URIs — replace with a
    // minimal stub that triggers onload synchronously when src is set.
    globalThis.Image = class StubImage {
      onload: ((ev: Event) => void) | null = null;
      complete = false;
      _src = "";
      get src() {
        return this._src;
      }
      set src(value: string) {
        this._src = value;
        this.complete = true;
        if (this.onload) {
          this.onload(new Event("load"));
        }
      }
    } as unknown as typeof Image;
  });

  afterEach(() => {
    globalThis.Image = OriginalImage;
  });

  const defaultProps = {
    sseActive: false,
    onToggleSSE: vi.fn(),
    confidenceThreshold: 0.5,
  };

  // 1.1 Happy Path — Idle State

  it("test_stream_viewer_shows_inactive_text_when_sse_off", () => {
    render(<StreamViewer {...defaultProps} sseActive={false} />);
    expect(screen.getByText("Stream inactive")).toBeInTheDocument();
  });

  it("test_stream_viewer_shows_inactive_text_before_first_frame", () => {
    mockUseStream.mockReturnValue({ frame: null });
    render(<StreamViewer {...defaultProps} sseActive={true} />);
    expect(screen.getByText("Stream inactive")).toBeInTheDocument();
  });

  // 1.2 Happy Path — Frame Rendering

  it("test_stream_viewer_draws_image_on_canvas", () => {
    const frame: FrameData = {
      jpeg_b64: "dGVzdA==",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };
    mockUseStream.mockReturnValue({ frame });

    render(<StreamViewer {...defaultProps} sseActive={true} />);

    expect(mockCtx.drawImage).toHaveBeenCalled();
  });

  it("test_stream_viewer_replaces_previous_frame", () => {
    const frame1: FrameData = {
      jpeg_b64: "ZnJhbWUx",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };
    const frame2: FrameData = {
      jpeg_b64: "ZnJhbWUy",
      timestamp: 2.0,
      source: "local:0",
      detections: [],
    };

    mockUseStream.mockReturnValue({ frame: frame1 });
    const { rerender } = render(<StreamViewer {...defaultProps} sseActive={true} />);

    mockUseStream.mockReturnValue({ frame: frame2 });
    rerender(<StreamViewer {...defaultProps} sseActive={true} />);

    expect(mockCtx.drawImage).toHaveBeenCalledTimes(2);
  });

  // 1.3 Happy Path — Bounding Box Rendering

  it("test_stream_viewer_draws_bbox_for_target_detection", () => {
    const frame: FrameData = {
      jpeg_b64: "dGVzdA==",
      timestamp: 1.0,
      source: "local:0",
      detections: [
        {
          label: "cat",
          confidence: 0.87,
          bounding_box: [0.1, 0.2, 0.4, 0.6],
          is_target: true,
        },
      ],
    };
    mockUseStream.mockReturnValue({ frame });

    render(<StreamViewer {...defaultProps} sseActive={true} />);

    expect(mockCtx.strokeRect).toHaveBeenCalled();
  });

  it("test_stream_viewer_draws_label_text_for_target", () => {
    const frame: FrameData = {
      jpeg_b64: "dGVzdA==",
      timestamp: 1.0,
      source: "local:0",
      detections: [
        {
          label: "cat",
          confidence: 0.87,
          bounding_box: [0.1, 0.2, 0.4, 0.6],
          is_target: true,
        },
      ],
    };
    mockUseStream.mockReturnValue({ frame });

    render(<StreamViewer {...defaultProps} sseActive={true} />);

    expect(mockCtx.fillText).toHaveBeenCalledWith(
      "cat 87%",
      expect.any(Number),
      expect.any(Number),
    );
  });

  it("test_stream_viewer_skips_non_target_detection", () => {
    const frame: FrameData = {
      jpeg_b64: "dGVzdA==",
      timestamp: 1.0,
      source: "local:0",
      detections: [
        {
          label: "bicycle",
          confidence: 0.65,
          bounding_box: [0.1, 0.2, 0.4, 0.6],
          is_target: false,
        },
      ],
    };
    mockUseStream.mockReturnValue({ frame });

    render(<StreamViewer {...defaultProps} sseActive={true} />);

    expect(mockCtx.strokeRect).not.toHaveBeenCalled();
  });

  it("test_stream_viewer_draws_multiple_target_bboxes", () => {
    const frame: FrameData = {
      jpeg_b64: "dGVzdA==",
      timestamp: 1.0,
      source: "local:0",
      detections: [
        {
          label: "cat",
          confidence: 0.87,
          bounding_box: [0.1, 0.2, 0.4, 0.6],
          is_target: true,
        },
        {
          label: "bicycle",
          confidence: 0.65,
          bounding_box: [0.5, 0.5, 0.7, 0.8],
          is_target: false,
        },
        {
          label: "dog",
          confidence: 0.91,
          bounding_box: [0.6, 0.1, 0.9, 0.5],
          is_target: true,
        },
      ],
    };
    mockUseStream.mockReturnValue({ frame });

    render(<StreamViewer {...defaultProps} sseActive={true} />);

    expect(mockCtx.strokeRect).toHaveBeenCalledTimes(2);
  });

  it("test_stream_viewer_bbox_coordinates_normalised_to_canvas", () => {
    const frame: FrameData = {
      jpeg_b64: "dGVzdA==",
      timestamp: 1.0,
      source: "local:0",
      detections: [
        {
          label: "cat",
          confidence: 0.9,
          bounding_box: [0.1, 0.2, 0.5, 0.8],
          is_target: true,
        },
      ],
    };
    mockUseStream.mockReturnValue({ frame });

    render(<StreamViewer {...defaultProps} sseActive={true} />);

    // canvas 800x450: x1=80, y1=90, w=(0.5-0.1)*800=320, h=(0.8-0.2)*450≈270
    expect(mockCtx.strokeRect).toHaveBeenCalledTimes(1);
    const args = mockCtx.strokeRect.mock.calls[0];
    expect(args[0]).toBeCloseTo(80, 5);
    expect(args[1]).toBeCloseTo(90, 5);
    expect(args[2]).toBeCloseTo(320, 5);
    expect(args[3]).toBeCloseTo(270, 5);
  });

  // 1.4 Happy Path — Confidence Threshold Display

  it("test_stream_viewer_shows_confidence_threshold", () => {
    render(<StreamViewer {...defaultProps} confidenceThreshold={0.5} />);
    expect(screen.getByText("Confidence Threshold: 0.50")).toBeInTheDocument();
  });

  it("test_stream_viewer_hides_confidence_when_null", () => {
    render(<StreamViewer {...defaultProps} confidenceThreshold={null} />);
    expect(screen.queryByText(/confidence threshold/i)).not.toBeInTheDocument();
  });

  // 1.5 Happy Path — SSE Activation

  it("test_stream_viewer_activates_hook_when_sse_on", () => {
    render(<StreamViewer {...defaultProps} sseActive={true} />);
    expect(mockUseStream).toHaveBeenCalledWith(true);
  });

  it("test_stream_viewer_deactivates_hook_when_sse_off", () => {
    render(<StreamViewer {...defaultProps} sseActive={false} />);
    expect(mockUseStream).toHaveBeenCalledWith(false);
  });
});
