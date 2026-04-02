import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useConfig } from "../../../src/ui/src/hooks/useConfig";

interface RuntimeConfig {
  camera:
    | { source_type: "local"; device_index: number }
    | { source_type: "rtsp"; rtsp_url: string };
  confidence_threshold: number;
  target_labels: string[];
}

const mockConfig: RuntimeConfig = {
  camera: { source_type: "local", device_index: 0 },
  confidence_threshold: 0.5,
  target_labels: ["cat"],
};

const mockLabels = { valid_labels: ["cat", "dog", "person"] };

function mockFetchSuccess(config = mockConfig, labels = mockLabels) {
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === "string" ? url : url.toString();
    if (urlStr.endsWith("/config/labels")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(labels),
      } as Response);
    }
    if (urlStr.endsWith("/config")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(config),
      } as Response);
    }
    return Promise.reject(new Error("unexpected url"));
  }) as typeof fetch;
}

function mockFetchResponses(responses: Record<string, { ok: boolean; status: number; body?: unknown }>) {
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === "string" ? url : url.toString();
    for (const [pattern, resp] of Object.entries(responses)) {
      if (urlStr.endsWith(pattern)) {
        if (!resp.ok) {
          return Promise.resolve({
            ok: false,
            status: resp.status,
            text: () => Promise.resolve(typeof resp.body === "string" ? resp.body : JSON.stringify(resp.body ?? "")),
            json: () => Promise.resolve(resp.body),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          status: resp.status,
          json: () => Promise.resolve(resp.body),
        } as Response);
      }
    }
    return Promise.reject(new Error("unexpected url"));
  }) as typeof fetch;
}

describe("useConfig", () => {
  let alertSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    mockFetchSuccess();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // 1.1 Happy Path — Initialisation

  it("test_use_config_loading_true_initially", () => {
    const { result } = renderHook(() => useConfig());
    expect(result.current.loading).toBe(true);
  });

  it("test_use_config_loading_false_after_fetch", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it("test_use_config_fetches_runtime_config", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => {
      expect(result.current.runtimeConfig).toEqual(mockConfig);
    });
  });

  it("test_use_config_fetches_valid_labels", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => {
      expect(result.current.validLabels).toEqual(["cat", "dog", "person"]);
    });
  });

  it("test_use_config_parallel_fetch", async () => {
    let fetchCallCount = 0;
    let firstResolve: (() => void) | null = null;

    global.fetch = vi.fn(() => {
      fetchCallCount++;
      return new Promise<Response>((resolve) => {
        if (!firstResolve) {
          firstResolve = () =>
            resolve({
              ok: true,
              status: 200,
              json: () => Promise.resolve(mockConfig),
            } as Response);
        } else {
          resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(mockLabels),
          } as Response);
        }
      });
    }) as typeof fetch;

    renderHook(() => useConfig());

    // Both fetches should be initiated before either resolves
    await waitFor(() => {
      expect(fetchCallCount).toBe(2);
    });

    firstResolve!();
  });

  // 1.2 Error Propagation — Initialisation

  it("test_use_config_get_config_error_alerts", async () => {
    mockFetchResponses({
      "/config/labels": { ok: true, status: 200, body: mockLabels },
      "/config": { ok: false, status: 500, body: "Internal Server Error" },
    });

    renderHook(() => useConfig());

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith("Error 500: Internal Server Error");
    });
  });

  it("test_use_config_get_config_error_sets_null", async () => {
    mockFetchResponses({
      "/config/labels": { ok: true, status: 200, body: mockLabels },
      "/config": { ok: false, status: 500, body: "Internal Server Error" },
    });

    const { result } = renderHook(() => useConfig());

    await waitFor(() => {
      expect(result.current.runtimeConfig).toBeNull();
    });
  });

  it("test_use_config_get_labels_error_alerts", async () => {
    mockFetchResponses({
      "/config/labels": { ok: false, status: 422, body: "Validation error" },
      "/config": { ok: true, status: 200, body: mockConfig },
    });

    renderHook(() => useConfig());

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });
  });

  it("test_use_config_get_labels_error_sets_empty", async () => {
    mockFetchResponses({
      "/config/labels": { ok: false, status: 422, body: "Validation error" },
      "/config": { ok: true, status: 200, body: mockConfig },
    });

    const { result } = renderHook(() => useConfig());

    await waitFor(() => {
      expect(result.current.validLabels).toEqual([]);
    });
  });

  it("test_use_config_network_error_alerts_404", async () => {
    global.fetch = vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))) as typeof fetch;

    renderHook(() => useConfig());

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith("Error 404: Server unreachable");
    });
  });

  it("test_use_config_partial_failure_config_succeeds", async () => {
    mockFetchResponses({
      "/config/labels": { ok: false, status: 500, body: "error" },
      "/config": { ok: true, status: 200, body: mockConfig },
    });

    const { result } = renderHook(() => useConfig());

    await waitFor(() => {
      expect(result.current.runtimeConfig).toEqual(mockConfig);
      expect(result.current.validLabels).toEqual([]);
    });
  });

  it("test_use_config_partial_failure_labels_succeeds", async () => {
    mockFetchResponses({
      "/config/labels": { ok: true, status: 200, body: mockLabels },
      "/config": { ok: false, status: 500, body: "error" },
    });

    const { result } = renderHook(() => useConfig());

    await waitFor(() => {
      expect(result.current.runtimeConfig).toBeNull();
      expect(result.current.validLabels).toEqual(["cat", "dog", "person"]);
    });
  });

  it("test_use_config_loading_false_after_failure", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve("error"),
      } as Response),
    ) as typeof fetch;

    const { result } = renderHook(() => useConfig());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  // 1.3 Happy Path — updateCamera

  it("test_use_config_update_camera_sends_put", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const updatedConfig = { ...mockConfig, camera: { source_type: "local" as const, device_index: 1 } };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    await act(() => result.current.updateCamera({ source_type: "local", device_index: 1 }));

    const lastCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    expect(lastCall[0]).toContain("/config/camera");
    expect(lastCall[1]?.method).toBe("PUT");
    const body = JSON.parse(lastCall[1]?.body as string);
    expect(body).toEqual({ camera: { source_type: "local", device_index: 1 } });
  });

  it("test_use_config_update_camera_success_updates_state", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const updatedConfig: RuntimeConfig = {
      ...mockConfig,
      camera: { source_type: "local", device_index: 5 },
    };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    await act(() => result.current.updateCamera({ source_type: "local", device_index: 5 }));

    expect(result.current.runtimeConfig).toEqual(updatedConfig);
  });

  it("test_use_config_update_camera_success_resolves", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockConfig),
    } as Response);

    await expect(
      act(() => result.current.updateCamera({ source_type: "local", device_index: 0 })),
    ).resolves.not.toThrow();
  });

  // 1.4 Error Propagation — updateCamera

  it("test_use_config_update_camera_422_alerts", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation failed"),
    } as Response);

    await act(async () => {
      try {
        await result.current.updateCamera({ source_type: "local", device_index: -1 });
      } catch {
        // expected
      }
    });

    expect(alertSpy).toHaveBeenCalledWith("Error 422: Validation failed");
  });

  it("test_use_config_update_camera_error_preserves_state", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const originalConfig = result.current.runtimeConfig;

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation failed"),
    } as Response);

    await act(async () => {
      try {
        await result.current.updateCamera({ source_type: "local", device_index: -1 });
      } catch {
        // expected
      }
    });

    expect(result.current.runtimeConfig).toEqual(originalConfig);
  });

  it("test_use_config_update_camera_error_rejects", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve("Bad Request"),
    } as Response);

    await expect(
      act(() => result.current.updateCamera({ source_type: "local", device_index: 0 })),
    ).rejects.toThrow();
  });

  it("test_use_config_update_camera_network_error", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new TypeError("Failed to fetch"),
    );

    await act(async () => {
      try {
        await result.current.updateCamera({ source_type: "local", device_index: 0 });
      } catch {
        // expected
      }
    });

    expect(alertSpy).toHaveBeenCalledWith("Error 404: Server unreachable");
  });

  // 1.5 Happy Path — updateLabels

  it("test_use_config_update_labels_sends_put", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const updatedConfig = { ...mockConfig, target_labels: ["cat", "dog"] };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    await act(() => result.current.updateLabels(["cat", "dog"]));

    const lastCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    expect(lastCall[0]).toContain("/config/labels");
    expect(lastCall[1]?.method).toBe("PUT");
    const body = JSON.parse(lastCall[1]?.body as string);
    expect(body).toEqual({ target_labels: ["cat", "dog"] });
  });

  it("test_use_config_update_labels_success_updates_state", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const updatedConfig: RuntimeConfig = { ...mockConfig, target_labels: ["cat", "dog"] };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    await act(() => result.current.updateLabels(["cat", "dog"]));

    expect(result.current.runtimeConfig).toEqual(updatedConfig);
  });

  it("test_use_config_update_labels_empty_array", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const updatedConfig = { ...mockConfig, target_labels: [] };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    await act(() => result.current.updateLabels([]));

    const lastCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    const body = JSON.parse(lastCall[1]?.body as string);
    expect(body).toEqual({ target_labels: [] });
  });

  // 1.6 Error Propagation — updateLabels

  it("test_use_config_update_labels_422_alerts", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation failed"),
    } as Response);

    await act(async () => {
      try {
        await result.current.updateLabels(["invalid"]);
      } catch {
        // expected
      }
    });

    expect(alertSpy).toHaveBeenCalledWith("Error 422: Validation failed");
  });

  it("test_use_config_update_labels_error_preserves_state", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const originalConfig = result.current.runtimeConfig;

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation failed"),
    } as Response);

    await act(async () => {
      try {
        await result.current.updateLabels(["invalid"]);
      } catch {
        // expected
      }
    });

    expect(result.current.runtimeConfig).toEqual(originalConfig);
  });

  it("test_use_config_update_labels_error_rejects", async () => {
    const { result } = renderHook(() => useConfig());
    await waitFor(() => expect(result.current.loading).toBe(false));

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve("Bad Request"),
    } as Response);

    await expect(
      act(() => result.current.updateLabels([])),
    ).rejects.toThrow();
  });
});
