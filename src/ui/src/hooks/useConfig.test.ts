import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import {
  buildRuntimeConfig,
  buildRtspCamera,
} from "../test-helpers/fixtures";

/**
 * Test Specification: useConfig.test.ts
 *
 * Source: src/ui/src/hooks/useConfig.ts
 * Status: scaffolded — production hook not yet implemented
 *
 * Missing production surface: useConfig hook export from ./useConfig
 */

// Placeholder: will import from "./useConfig" once available
// import { useConfig } from "./useConfig";
const useConfig = (): {
  runtimeConfig: unknown;
  validLabels: string[];
  loading: boolean;
  updateCamera: (camera: unknown) => Promise<void>;
  updateLabels: (labels: string[]) => Promise<void>;
} => ({
  runtimeConfig: null,
  validLabels: [],
  loading: false,
  updateCamera: async () => {},
  updateLabels: async () => {},
});

// --- Test Helpers ---

const CONFIG_RESPONSE = buildRuntimeConfig();
const LABELS_RESPONSE = { valid_labels: ["cat", "dog"] };

function mockFetchSuccess() {
  return vi.fn((url: string) => {
    if (url === "/config") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(CONFIG_RESPONSE),
        text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
      });
    }
    if (url === "/config/labels") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(LABELS_RESPONSE),
        text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
      });
    }
    return Promise.reject(new TypeError("Failed to fetch"));
  });
}

let alertSpy: ReturnType<typeof vi.spyOn>;
let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
  originalFetch = globalThis.fetch;
});

afterEach(() => {
  alertSpy.mockRestore();
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("useConfig", () => {
  describe("Happy Path — Initialization", () => {
    it("fetches_config_and_labels_on_mount", async () => {
      // Setup: Mock fetch for both /config and /config/labels
      globalThis.fetch = mockFetchSuccess() as unknown as typeof fetch;
      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(result.current.runtimeConfig).toEqual(CONFIG_RESPONSE);
      expect(result.current.validLabels).toEqual(["cat", "dog"]);
    });

    it("loading_true_initially", () => {
      // Setup: fetch returns pending promises
      globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;
      const { result } = renderHook(() => useConfig());
      expect(result.current.loading).toBe(true);
    });

    it("loading_false_after_both_settle", async () => {
      globalThis.fetch = mockFetchSuccess() as unknown as typeof fetch;
      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });
  });

  describe("Error Propagation", () => {
    it("alerts_on_config_fetch_non_ok", async () => {
      globalThis.fetch = vi.fn((url: string) => {
        if (url === "/config") {
          return Promise.resolve({
            ok: false,
            status: 500,
            text: () => Promise.resolve("Internal error"),
          });
        }
        if (url === "/config/labels") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(alertSpy).toHaveBeenCalledWith("Error 500: Internal error");
      expect(result.current.runtimeConfig).toBeNull();
    });

    it("alerts_on_labels_fetch_non_ok", async () => {
      globalThis.fetch = vi.fn((url: string) => {
        if (url === "/config") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels") {
          return Promise.resolve({
            ok: false,
            status: 404,
            text: () => Promise.resolve("Not found"),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(alertSpy).toHaveBeenCalledWith("Error 404: Not found");
      expect(result.current.validLabels).toEqual([]);
    });

    it("alerts_on_network_error_config", async () => {
      globalThis.fetch = vi.fn((url: string) => {
        if (url === "/config") {
          return Promise.reject(new TypeError("Failed to fetch"));
        }
        if (url === "/config/labels") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(alertSpy).toHaveBeenCalledWith("Error 404: Server unreachable");
      expect(result.current.runtimeConfig).toBeNull();
    });

    it("alerts_on_network_error_labels", async () => {
      globalThis.fetch = vi.fn((url: string) => {
        if (url === "/config") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels") {
          return Promise.reject(new TypeError("Failed to fetch"));
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(alertSpy).toHaveBeenCalledWith("Error 404: Server unreachable");
      expect(result.current.validLabels).toEqual([]);
    });

    it("both_fail_produces_two_alerts", async () => {
      globalThis.fetch = vi.fn(() =>
        Promise.reject(new TypeError("Failed to fetch"))
      ) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(alertSpy).toHaveBeenCalledTimes(2);
      expect(result.current.runtimeConfig).toBeNull();
      expect(result.current.validLabels).toEqual([]);
    });
  });

  describe("Happy Path — updateCamera", () => {
    it("update_camera_sends_put_and_updates_state", async () => {
      const updatedConfig = buildRuntimeConfig({
        camera: buildRtspCamera({ rtsp_url: "rtsp://new" }),
      });
      const fetchMock = vi.fn((url: string, opts?: RequestInit) => {
        if (url === "/config" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        if (url === "/config/camera" && opts?.method === "PUT") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(updatedConfig),
            text: () => Promise.resolve(JSON.stringify(updatedConfig)),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;
      globalThis.fetch = fetchMock;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.updateCamera({
          source_type: "rtsp",
          rtsp_url: "rtsp://new",
        });
      });

      // Verify PUT was called correctly
      expect(fetchMock).toHaveBeenCalledWith(
        "/config/camera",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ camera: { source_type: "rtsp", rtsp_url: "rtsp://new" } }),
        })
      );
      expect(result.current.runtimeConfig).toEqual(updatedConfig);
    });

    it("update_camera_alerts_and_rejects_on_error", async () => {
      globalThis.fetch = vi.fn((url: string, opts?: RequestInit) => {
        if (url === "/config" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        if (url === "/config/camera" && opts?.method === "PUT") {
          return Promise.resolve({
            ok: false,
            status: 422,
            text: () => Promise.resolve("Invalid"),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let rejected = false;
      await act(async () => {
        try {
          await result.current.updateCamera({ source_type: "local", device_index: 0 });
        } catch {
          rejected = true;
        }
      });

      expect(rejected).toBe(true);
      expect(alertSpy).toHaveBeenCalledWith("Error 422: Invalid");
      expect(result.current.runtimeConfig).toEqual(CONFIG_RESPONSE);
    });

    it("update_camera_alerts_on_network_error", async () => {
      globalThis.fetch = vi.fn((url: string, opts?: RequestInit) => {
        if (url === "/config" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        if (url === "/config/camera" && opts?.method === "PUT") {
          return Promise.reject(new TypeError("Failed to fetch"));
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let rejected = false;
      await act(async () => {
        try {
          await result.current.updateCamera({ source_type: "local", device_index: 0 });
        } catch {
          rejected = true;
        }
      });

      expect(rejected).toBe(true);
      expect(alertSpy).toHaveBeenCalledWith("Error 404: Server unreachable");
    });
  });

  describe("Happy Path — updateLabels", () => {
    it("update_labels_sends_put_and_updates_state", async () => {
      const updatedConfig = buildRuntimeConfig({ target_labels: ["cat", "dog"] });
      globalThis.fetch = vi.fn((url: string, opts?: RequestInit) => {
        if (url === "/config" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        if (url === "/config/labels" && opts?.method === "PUT") {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(updatedConfig),
            text: () => Promise.resolve(JSON.stringify(updatedConfig)),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.updateLabels(["cat", "dog"]);
      });

      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/config/labels",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ target_labels: ["cat", "dog"] }),
        })
      );
      expect(result.current.runtimeConfig).toEqual(updatedConfig);
    });

    it("update_labels_alerts_and_rejects_on_error", async () => {
      globalThis.fetch = vi.fn((url: string, opts?: RequestInit) => {
        if (url === "/config" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(CONFIG_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(CONFIG_RESPONSE)),
          });
        }
        if (url === "/config/labels" && (!opts || opts.method !== "PUT")) {
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(LABELS_RESPONSE),
            text: () => Promise.resolve(JSON.stringify(LABELS_RESPONSE)),
          });
        }
        if (url === "/config/labels" && opts?.method === "PUT") {
          return Promise.resolve({
            ok: false,
            status: 400,
            text: () => Promise.resolve("Bad request"),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let rejected = false;
      await act(async () => {
        try {
          await result.current.updateLabels([]);
        } catch {
          rejected = true;
        }
      });

      expect(rejected).toBe(true);
      expect(alertSpy).toHaveBeenCalledWith("Error 400: Bad request");
      expect(result.current.runtimeConfig).toEqual(CONFIG_RESPONSE);
    });
  });

  describe("Idempotency", () => {
    it("update_camera_is_referentially_stable", async () => {
      globalThis.fetch = mockFetchSuccess() as unknown as typeof fetch;
      const { result, rerender } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      const first = result.current.updateCamera;
      rerender();
      expect(result.current.updateCamera).toBe(first);
    });

    it("update_labels_is_referentially_stable", async () => {
      globalThis.fetch = mockFetchSuccess() as unknown as typeof fetch;
      const { result, rerender } = renderHook(() => useConfig());
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      const first = result.current.updateLabels;
      rerender();
      expect(result.current.updateLabels).toBe(first);
    });
  });

  describe("Asynchronous Flow", () => {
    it("update_camera_during_initial_load", async () => {
      const updatedConfig = buildRuntimeConfig({
        camera: buildRtspCamera({ rtsp_url: "rtsp://early" }),
      });
      // /config never resolves (pending), but PUT resolves
      globalThis.fetch = vi.fn((url: string, opts?: RequestInit) => {
        if (url === "/config" && (!opts || opts.method !== "PUT")) {
          return new Promise(() => {}); // never resolves
        }
        if (url === "/config/labels" && (!opts || opts.method !== "PUT")) {
          return new Promise(() => {}); // never resolves
        }
        if (url === "/config/camera" && opts?.method === "PUT") {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(updatedConfig),
            text: () => Promise.resolve(JSON.stringify(updatedConfig)),
          });
        }
        return Promise.reject(new TypeError("Failed to fetch"));
      }) as unknown as typeof fetch;

      const { result } = renderHook(() => useConfig());
      // loading is true because initial GET never resolves
      expect(result.current.loading).toBe(true);

      await act(async () => {
        await result.current.updateCamera({
          source_type: "rtsp",
          rtsp_url: "rtsp://early",
        });
      });

      // PUT sent and state updated despite initial load not done
      expect(result.current.runtimeConfig).toEqual(updatedConfig);
    });
  });
});
