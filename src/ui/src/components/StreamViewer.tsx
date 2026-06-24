/**
 * Component that renders the live detection stream on a canvas element.
 * Draws JPEG frames with bounding box overlays for target detections.
 */
import { useRef, useEffect } from "react";
import { useStream } from "../hooks/useStream";
import type { FrameData } from "../hooks/useStream";

interface StreamViewerProps {
  sseActive: boolean;
  onToggleSSE: (active: boolean) => void;
  confidenceThreshold: number | null;
}

const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 450;

function drawFrame(ctx: CanvasRenderingContext2D, frame: FrameData, img: HTMLImageElement): void {
  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  ctx.drawImage(img, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

  for (const detection of frame.detections) {
    if (!detection.is_target) continue;

    const [x1, y1, x2, y2] = detection.bounding_box;
    const x = x1 * CANVAS_WIDTH;
    const y = y1 * CANVAS_HEIGHT;
    const w = (x2 - x1) * CANVAS_WIDTH;
    const h = (y2 - y1) * CANVAS_HEIGHT;

    // Draw bounding box
    ctx.strokeStyle = "#5B8CB8";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    // Draw label
    const labelText = `${detection.label} ${Math.round(detection.confidence * 100)}%`;
    ctx.font = "14px sans-serif";
    const textMetrics = ctx.measureText(labelText);
    const textWidth = textMetrics.width + 8;
    const textHeight = 18;

    // Label background
    ctx.fillStyle = "#5B8CB8";
    ctx.fillRect(x, y - textHeight, textWidth, textHeight);

    // Label text
    ctx.fillStyle = "#FFFFFF";
    ctx.fillText(labelText, x + 4, y - 4);
  }
}

export function StreamViewer({ sseActive, onToggleSSE: _onToggleSSE, confidenceThreshold }: StreamViewerProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { frame } = useStream(sseActive);

  useEffect(() => {
    if (!frame) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let drawn = false;
    const img = new Image();
    img.onload = () => {
      if (!drawn) {
        drawn = true;
        drawFrame(ctx, frame, img);
      }
    };
    img.src = `data:image/jpeg;base64,${frame.jpeg_b64}`;
    // Handle synchronous complete (cached images)
    if (img.complete && !drawn) {
      drawn = true;
      drawFrame(ctx, frame, img);
    }
  }, [frame]);

  const showCanvas = sseActive && frame !== null;

  return (
    <div>
      {!showCanvas && (
        <div
          style={{
            aspectRatio: "16/9",
            background: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ color: "#6B7B8D" }}>Stream inactive</span>
        </div>
      )}
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        style={{
          width: "100%",
          aspectRatio: "16/9",
          display: showCanvas ? "block" : "none",
        }}
      />
      {confidenceThreshold !== null && (
        <div style={{ textAlign: "right", color: "#6B7B8D", fontSize: "0.8rem" }}>
          Confidence Threshold: {confidenceThreshold.toFixed(2)}
        </div>
      )}
    </div>
  );
}
