/**
 * Custom React hook that manages an SSE connection to /stream
 * and provides the latest frame data for rendering.
 */
import { useState, useEffect, useRef } from "react";

export interface Detection {
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number];
  is_target: boolean;
}

export interface FrameData {
  jpeg_b64: string;
  timestamp: number;
  source: string;
  detections: Detection[];
}

export function useStream(active: boolean): { frame: FrameData | null } {
  const [frame, setFrame] = useState<FrameData | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (active) {
      const es = new EventSource("/stream");
      esRef.current = es;

      es.addEventListener("message", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as FrameData;
          setFrame(data);
        } catch (e) {
          console.error("Failed to parse frame data:", e);
        }
      });

      es.addEventListener("error", () => {
        // Silent — EventSource reconnects automatically
      });

      return () => {
        es.close();
        esRef.current = null;
      };
    } else {
      setFrame(null);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      return undefined;
    }
  }, [active]);

  return { frame };
}
