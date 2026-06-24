/**
 * Custom React hook that encapsulates all communication with the Config API.
 * Provides runtime configuration, valid labels, loading state, and mutation functions.
 */
import { useState, useEffect, useCallback } from "react";

export type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };

export interface RuntimeConfig {
  camera: CameraConfigData;
  confidence_threshold: number;
  target_labels: string[];
}

export interface UseConfigReturn {
  runtimeConfig: RuntimeConfig | null;
  validLabels: string[];
  loading: boolean;
  updateCamera: (camera: CameraConfigData) => Promise<void>;
  updateLabels: (labels: string[]) => Promise<void>;
}

async function handleResponse(response: Response): Promise<never> {
  const message = await response.text();
  const errorMsg = `Error ${response.status}: ${message}`;
  window.alert(errorMsg);
  throw new Error(errorMsg);
}

function handleNetworkError(error: unknown): never {
  if (error instanceof TypeError) {
    const errorMsg = "Error 404: Server unreachable";
    window.alert(errorMsg);
    throw new Error(errorMsg);
  }
  throw error;
}

export function useConfig(): UseConfigReturn {
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [validLabels, setValidLabels] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;

    async function fetchConfig() {
      try {
        const response = await fetch("/config");
        if (!response.ok) {
          const message = await response.text();
          window.alert(`Error ${response.status}: ${message}`);
          return;
        }
        const data = (await response.json()) as RuntimeConfig;
        if (mounted) {
          setRuntimeConfig(data);
        }
      } catch (error) {
        if (error instanceof TypeError) {
          window.alert("Error 404: Server unreachable");
        }
      }
    }

    async function fetchLabels() {
      try {
        const response = await fetch("/config/labels");
        if (!response.ok) {
          const message = await response.text();
          window.alert(`Error ${response.status}: ${message}`);
          return;
        }
        const data = (await response.json()) as { valid_labels: string[] };
        if (mounted) {
          setValidLabels(data.valid_labels);
        }
      } catch (error) {
        if (error instanceof TypeError) {
          window.alert("Error 404: Server unreachable");
        }
      }
    }

    Promise.allSettled([fetchConfig(), fetchLabels()]).then(() => {
      if (mounted) {
        setLoading(false);
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  const updateCamera = useCallback(async (camera: CameraConfigData): Promise<void> => {
    try {
      const response = await fetch("/config/camera", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera }),
      });
      if (!response.ok) {
        await handleResponse(response);
      }
      const data = (await response.json()) as RuntimeConfig;
      setRuntimeConfig(data);
    } catch (error) {
      if (error instanceof TypeError) {
        handleNetworkError(error);
      }
      throw error;
    }
  }, []);

  const updateLabels = useCallback(async (labels: string[]): Promise<void> => {
    try {
      const response = await fetch("/config/labels", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_labels: labels }),
      });
      if (!response.ok) {
        await handleResponse(response);
      }
      const data = (await response.json()) as RuntimeConfig;
      setRuntimeConfig(data);
    } catch (error) {
      if (error instanceof TypeError) {
        handleNetworkError(error);
      }
      throw error;
    }
  }, []);

  return { runtimeConfig, validLabels, loading, updateCamera, updateLabels };
}
