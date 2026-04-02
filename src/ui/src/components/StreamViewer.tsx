import { useRef, useEffect } from "react";
import { useStream, type FrameData } from "../hooks/useStream";

interface StreamViewerProps {
  sseActive: boolean;
  onToggleSSE: (active: boolean) => void;
  confidenceThreshold: number | null;
}

function drawFrame(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  frame: FrameData,
) {
  const w = ctx.canvas.width;
  const h = ctx.canvas.height;

  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(img, 0, 0, w, h);

  for (const det of frame.detections) {
    if (!det.is_target) continue;

    const [x1, y1, x2, y2] = det.bounding_box;
    const px_x1 = x1 * w;
    const px_y1 = y1 * h;
    const px_w = (x2 - x1) * w;
    const px_h = (y2 - y1) * h;

    ctx.strokeStyle = "#5B8CB8";
    ctx.lineWidth = 2;
    ctx.strokeRect(px_x1, px_y1, px_w, px_h);

    const label = `${det.label} ${Math.round(det.confidence * 100)}%`;
    ctx.font = "14px sans-serif";
    const textMetrics = ctx.measureText(label);
    const textHeight = 18;

    ctx.fillStyle = "#5B8CB8";
    ctx.fillRect(px_x1, px_y1 - textHeight, textMetrics.width + 8, textHeight);

    ctx.fillStyle = "#FFFFFF";
    ctx.fillText(label, px_x1 + 4, px_y1 - 4);
  }
}

export default function StreamViewer({
  sseActive,
  onToggleSSE: _onToggleSSE,
  confidenceThreshold,
}: StreamViewerProps) {
  const { frame } = useStream(sseActive);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frame) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    let drawn = false;
    img.onload = () => {
      if (!drawn) {
        drawn = true;
        drawFrame(ctx, img, frame);
      }
    };
    img.src = `data:image/jpeg;base64,${frame.jpeg_b64}`;

    // Handle environments where Image loads synchronously or doesn't fire onload
    if (img.complete && !drawn) {
      drawn = true;
      drawFrame(ctx, img, frame);
    }
  }, [frame]);

  const showInactive = !sseActive || !frame;

  return (
    <div>
      <div style={{ position: "relative" }}>
        <canvas
          ref={canvasRef}
          width={800}
          height={450}
          style={{
            width: "100%",
            aspectRatio: "16/9",
            backgroundColor: "#FFFFFF",
            borderRadius: "4px",
            display: showInactive ? "none" : "block",
          }}
        />
        {showInactive && (
          <div
            style={{
              width: "100%",
              aspectRatio: "16/9",
              backgroundColor: "#FFFFFF",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6B7B8D",
              fontSize: "1.1rem",
            }}
          >
            Stream inactive
          </div>
        )}
      </div>

      {confidenceThreshold !== null && (
        <div
          style={{
            textAlign: "right",
            color: "#6B7B8D",
            fontSize: "0.8rem",
            marginTop: "4px",
          }}
        >
          Confidence Threshold: {confidenceThreshold.toFixed(2)}
        </div>
      )}
    </div>
  );
}
