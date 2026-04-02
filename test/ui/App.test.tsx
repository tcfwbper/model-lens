import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../src/ui/src/App";

interface RuntimeConfig {
  camera:
    | { source_type: "local"; device_index: number }
    | { source_type: "rtsp"; rtsp_url: string };
  confidence_threshold: number;
  target_labels: string[];
}

const mockConfig: RuntimeConfig = {
  camera: { source_type: "local", device_index: 2 },
  confidence_threshold: 0.5,
  target_labels: ["cat", "dog"],
};

const mockLabels = { valid_labels: ["person", "cat", "dog"] };

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

describe("App", () => {
  let alertSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    mockFetchSuccess();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // 1.1 Happy Path — Page Load

  it("test_app_renders_header", async () => {
    render(<App />);
    expect(screen.getByText("ModelLens")).toBeInTheDocument();
  });

  it("test_app_fetches_config_on_mount", async () => {
    render(<App />);
    await waitFor(() => {
      const calls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const configCall = calls.find((c: unknown[]) => (c[0] as string).endsWith("/config") && !(c[0] as string).endsWith("/config/labels"));
      expect(configCall).toBeDefined();
    });
  });

  it("test_app_fetches_labels_on_mount", async () => {
    render(<App />);
    await waitFor(() => {
      const calls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const labelsCall = calls.find((c: unknown[]) => (c[0] as string).endsWith("/config/labels"));
      expect(labelsCall).toBeDefined();
    });
  });

  it("test_app_parallel_fetch_on_mount", async () => {
    let resolveCount = 0;
    let fetchCallsBeforeResolve = 0;

    global.fetch = vi.fn(() => {
      fetchCallsBeforeResolve++;
      return new Promise<Response>((resolve) => {
        setTimeout(() => {
          resolveCount++;
          resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(resolveCount === 1 ? mockConfig : mockLabels),
          } as Response);
        }, 0);
      });
    }) as typeof fetch;

    render(<App />);

    // Both fetches should be initiated synchronously before any resolves
    expect(fetchCallsBeforeResolve).toBe(2);

    await waitFor(() => expect(resolveCount).toBe(2));
  });

  it("test_app_displays_camera_config_from_server", async () => {
    render(<App />);
    await waitFor(() => {
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect(select.value).toBe("local");
    });
    await waitFor(() => {
      expect(screen.getByDisplayValue("2")).toBeInTheDocument();
    });
  });

  it("test_app_displays_target_labels_from_server", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("2 labels selected")).toBeInTheDocument();
    });
  });

  it("test_app_populates_valid_labels_dropdown", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/labels selected/)).toBeInTheDocument();
    });

    // Open the dropdown
    await user.click(screen.getByText(/labels selected/));

    expect(screen.getByText("person")).toBeInTheDocument();
    expect(screen.getByText("cat")).toBeInTheDocument();
    expect(screen.getByText("dog")).toBeInTheDocument();
  });

  it("test_app_displays_confidence_threshold", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Confidence Threshold: 0.50")).toBeInTheDocument();
    });
  });

  // 1.2 Happy Path — Camera Update

  it("test_app_camera_update_success_refreshes_display", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("2")).toBeInTheDocument();
    });

    const updatedConfig: RuntimeConfig = {
      ...mockConfig,
      camera: { source_type: "rtsp", rtsp_url: "rtsp://10.0.0.1/feed" },
    };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    await user.selectOptions(screen.getByRole("combobox"), "rtsp");
    const urlInput = screen.getByPlaceholderText("rtsp://...");
    await user.type(urlInput, "rtsp://10.0.0.1/feed");
    await user.click(screen.getByRole("button", { name: /update camera/i }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("rtsp://10.0.0.1/feed")).toBeInTheDocument();
    });
  });

  // 1.3 Happy Path — Labels Update

  it("test_app_labels_update_success_refreshes_display", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("2 labels selected")).toBeInTheDocument();
    });

    const updatedConfig: RuntimeConfig = {
      ...mockConfig,
      target_labels: ["cat", "dog", "person"],
    };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updatedConfig),
    } as Response);

    // Open dropdown and toggle person
    await user.click(screen.getByText("2 labels selected"));
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const personCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("person"),
    )!;
    await user.click(personCheckbox);
    await user.click(screen.getByRole("button", { name: /update labels/i }));

    await waitFor(() => {
      expect(screen.getByText("All labels selected")).toBeInTheDocument();
    });
  });

  // 1.4 Happy Path — SSE Controls

  it("test_app_sse_default_inactive", async () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /start stream/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /stop stream/i })).toBeDisabled();
  });

  it("test_app_start_stream_button_activates_sse", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /start stream/i }));

    expect(screen.getByRole("button", { name: /start stream/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /stop stream/i })).toBeEnabled();
  });

  it("test_app_stop_stream_button_deactivates_sse", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /start stream/i }));
    await user.click(screen.getByRole("button", { name: /stop stream/i }));

    expect(screen.getByRole("button", { name: /start stream/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /stop stream/i })).toBeDisabled();
  });

  // 1.5 Error Propagation

  it("test_app_get_config_failure_shows_alert", async () => {
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.endsWith("/config/labels")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockLabels),
        } as Response);
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Internal Server Error"),
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith("Error 500: Internal Server Error");
    });
  });

  it("test_app_get_labels_failure_shows_alert", async () => {
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.endsWith("/config/labels")) {
        return Promise.resolve({
          ok: false,
          status: 500,
          text: () => Promise.resolve("Internal Server Error"),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockConfig),
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });
  });

  it("test_app_network_error_shows_alert_with_404", async () => {
    global.fetch = vi.fn(() =>
      Promise.reject(new TypeError("Failed to fetch")),
    ) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith("Error 404: Server unreachable");
    });
  });

  it("test_app_get_config_failure_renders_empty_defaults", async () => {
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.endsWith("/config/labels")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockLabels),
        } as Response);
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve("error"),
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });

    // Camera field should be empty
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("");

    // No confidence threshold displayed
    expect(screen.queryByText(/confidence threshold/i)).not.toBeInTheDocument();
  });

  it("test_app_get_labels_failure_renders_empty_dropdown", async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.endsWith("/config/labels")) {
        return Promise.resolve({
          ok: false,
          status: 500,
          text: () => Promise.resolve("error"),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockConfig),
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });

    // Open dropdown - should have no checkboxes
    await user.click(screen.getByText(/labels selected|no labels/i));
    expect(screen.queryAllByRole("checkbox").length).toBe(0);
  });

  it("test_app_partial_failure_config_only", async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.endsWith("/config/labels")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockLabels),
        } as Response);
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve("error"),
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });

    // Labels dropdown should still be populated
    await user.click(screen.getByText(/labels selected|no labels/i));
    expect(screen.getAllByRole("checkbox").length).toBe(3);

    // Camera should be empty
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("");
  });

  it("test_app_partial_failure_labels_only", async () => {
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.endsWith("/config/labels")) {
        return Promise.resolve({
          ok: false,
          status: 500,
          text: () => Promise.resolve("error"),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockConfig),
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("2")).toBeInTheDocument();
    });

    // Camera config should be populated
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("local");
  });
});
