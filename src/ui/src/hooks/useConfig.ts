import { useState, useEffect, useCallback } from "react";

export type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };

export interface RuntimeConfig {
  camera: CameraConfigData;
  confidence_threshold: number;
  target_labels: string[];
}

async function handleResponse(response: Response): Promise<never> {
  const message = await response.text();
  window.alert(`Error ${response.status}: ${message}`);
  throw new Error(`Error ${response.status}: ${message}`);
}

function handleNetworkError(error: unknown): never {
  if (error instanceof TypeError) {
    window.alert("Error 404: Server unreachable");
    throw new Error("Error 404: Server unreachable");
  }
  throw error;
}

export function useConfig() {
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [validLabels, setValidLabels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConfig = fetch("/config").then(async (res) => {
      if (!res.ok) {
        const message = await res.text();
        window.alert(`Error ${res.status}: ${message}`);
        return null;
      }
      return res.json() as Promise<RuntimeConfig>;
    }).catch((err) => {
      if (err instanceof TypeError) {
        window.alert("Error 404: Server unreachable");
      }
      return null;
    });

    const fetchLabels = fetch("/config/labels").then(async (res) => {
      if (!res.ok) {
        const message = await res.text();
        window.alert(`Error ${res.status}: ${message}`);
        return null;
      }
      return res.json() as Promise<{ valid_labels: string[] }>;
    }).catch((err) => {
      if (err instanceof TypeError) {
        window.alert("Error 404: Server unreachable");
      }
      return null;
    });

    Promise.all([fetchConfig, fetchLabels]).then(([config, labels]) => {
      if (config) setRuntimeConfig(config);
      if (labels) setValidLabels(labels.valid_labels);
      setLoading(false);
    });
  }, []);

  const updateCamera = useCallback(async (camera: CameraConfigData) => {
    try {
      const res = await fetch("/config/camera", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera }),
      });
      if (!res.ok) {
        await handleResponse(res);
      }
      const updated = (await res.json()) as RuntimeConfig;
      setRuntimeConfig(updated);
    } catch (err) {
      handleNetworkError(err);
    }
  }, []);

  const updateLabels = useCallback(async (labels: string[]) => {
    try {
      const res = await fetch("/config/labels", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_labels: labels }),
      });
      if (!res.ok) {
        await handleResponse(res);
      }
      const updated = (await res.json()) as RuntimeConfig;
      setRuntimeConfig(updated);
    } catch (err) {
      handleNetworkError(err);
    }
  }, []);

  return { runtimeConfig, validLabels, loading, updateCamera, updateLabels };
}
