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

export function useStream(active: boolean) {
  const [frame, setFrame] = useState<FrameData | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!active) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      setFrame(null);
      return;
    }

    const es = new EventSource("/stream");
    esRef.current = es;

    es.addEventListener("message", (event: MessageEvent) => {
      const data = JSON.parse(event.data) as FrameData;
      setFrame(data);
    });

    es.addEventListener("error", () => {
      // Silent — EventSource handles reconnection automatically
    });

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [active]);

  return { frame };
}
