import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CameraConfig from "../../../src/ui/src/components/CameraConfig";

type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };

describe("CameraConfig", () => {
  const localCamera: CameraConfigData = { source_type: "local", device_index: 0 };
  const rtspCamera: CameraConfigData = {
    source_type: "rtsp",
    rtsp_url: "rtsp://192.168.1.10/stream",
  };
  let onUpdate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onUpdate = vi.fn(() => Promise.resolve());
  });

  // 1.1 Happy Path — Rendering

  it("test_camera_config_renders_local_source", () => {
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("local");
    expect(screen.getByDisplayValue("0")).toBeInTheDocument();
  });

  it("test_camera_config_renders_rtsp_source", () => {
    render(<CameraConfig camera={rtspCamera} onUpdate={onUpdate} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("rtsp");
    expect(screen.getByDisplayValue("rtsp://192.168.1.10/stream")).toBeInTheDocument();
  });

  it("test_camera_config_renders_null_camera", () => {
    render(<CameraConfig camera={null} onUpdate={onUpdate} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("local");
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("");
  });

  // 1.2 Happy Path — Source Type Switching

  it("test_camera_config_switch_local_to_rtsp_shows_url_field", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    await user.selectOptions(screen.getByRole("combobox"), "rtsp");

    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("rtsp://...")).toBeInTheDocument();
  });

  it("test_camera_config_switch_rtsp_to_local_shows_index_field", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={rtspCamera} onUpdate={onUpdate} />);

    await user.selectOptions(screen.getByRole("combobox"), "local");

    expect(screen.queryByPlaceholderText("rtsp://...")).not.toBeInTheDocument();
    expect(screen.getByRole("spinbutton")).toBeInTheDocument();
  });

  it("test_camera_config_switch_clears_hidden_field", async () => {
    const user = userEvent.setup();
    const camera: CameraConfigData = { source_type: "local", device_index: 2 };
    render(<CameraConfig camera={camera} onUpdate={onUpdate} />);

    await user.selectOptions(screen.getByRole("combobox"), "rtsp");
    await user.selectOptions(screen.getByRole("combobox"), "local");

    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("");
  });

  // 1.3 Happy Path — Update Submission

  it("test_camera_config_update_local_calls_on_update", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "3");
    await user.click(screen.getByRole("button", { name: /update camera/i }));

    expect(onUpdate).toHaveBeenCalledWith({ source_type: "local", device_index: 3 });
  });

  it("test_camera_config_update_rtsp_calls_on_update", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    await user.selectOptions(screen.getByRole("combobox"), "rtsp");
    const input = screen.getByPlaceholderText("rtsp://...");
    await user.type(input, "rtsp://10.0.0.1/feed");
    await user.click(screen.getByRole("button", { name: /update camera/i }));

    expect(onUpdate).toHaveBeenCalledWith({
      source_type: "rtsp",
      rtsp_url: "rtsp://10.0.0.1/feed",
    });
  });

  it("test_camera_config_update_button_shows_loading", async () => {
    const user = userEvent.setup();
    let resolveUpdate!: () => void;
    onUpdate.mockReturnValue(new Promise<void>((r) => (resolveUpdate = r)));

    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "5");
    await user.click(screen.getByRole("button", { name: /update camera/i }));

    const button = screen.getByRole("button", { name: /updating/i });
    expect(button).toBeDisabled();

    resolveUpdate();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /update camera/i })).toBeInTheDocument();
    });
  });

  it("test_camera_config_update_success_resyncs_state", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <CameraConfig camera={localCamera} onUpdate={onUpdate} />,
    );

    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "5");
    await user.click(screen.getByRole("button", { name: /update camera/i }));

    const newCamera: CameraConfigData = { source_type: "local", device_index: 5 };
    rerender(<CameraConfig camera={newCamera} onUpdate={onUpdate} />);

    const updatedInput = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(updatedInput.value).toBe("5");
    expect(screen.getByRole("button", { name: /update camera/i })).toBeDisabled();
  });

  it("test_camera_config_update_failure_preserves_input", async () => {
    const user = userEvent.setup();
    onUpdate.mockRejectedValue(new Error("update failed"));

    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "7");
    await user.click(screen.getByRole("button", { name: /update camera/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /update camera/i })).toBeEnabled();
    });
    const preserved = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(preserved.value).toBe("7");
  });

  // 1.4 Dirty Detection

  it("test_camera_config_button_disabled_when_clean", () => {
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);
    expect(screen.getByRole("button", { name: /update camera/i })).toBeDisabled();
  });

  it("test_camera_config_button_enabled_when_type_changed", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    await user.selectOptions(screen.getByRole("combobox"), "rtsp");

    expect(screen.getByRole("button", { name: /update camera/i })).toBeEnabled();
  });

  it("test_camera_config_button_enabled_when_index_changed", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "1");

    expect(screen.getByRole("button", { name: /update camera/i })).toBeEnabled();
  });

  it("test_camera_config_button_enabled_when_url_changed", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={rtspCamera} onUpdate={onUpdate} />);

    const input = screen.getByDisplayValue("rtsp://192.168.1.10/stream");
    await user.clear(input);
    await user.type(input, "rtsp://new-url/stream");

    expect(screen.getByRole("button", { name: /update camera/i })).toBeEnabled();
  });

  it("test_camera_config_button_disabled_when_reverted", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={localCamera} onUpdate={onUpdate} />);

    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "5");
    await user.clear(input);
    await user.type(input, "0");

    expect(screen.getByRole("button", { name: /update camera/i })).toBeDisabled();
  });

  it("test_camera_config_button_enabled_when_null_camera_and_input", async () => {
    const user = userEvent.setup();
    render(<CameraConfig camera={null} onUpdate={onUpdate} />);

    const input = screen.getByRole("spinbutton");
    await user.type(input, "0");

    expect(screen.getByRole("button", { name: /update camera/i })).toBeEnabled();
  });
});
