import { describe, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { buildLocalCamera, buildRtspCamera } from "../test-helpers/fixtures";
import type { CameraConfigData } from "../test-helpers/fixtures";

/**
 * Test Specification: CameraConfig.test.tsx
 *
 * Source: src/ui/src/components/CameraConfig.tsx
 */

import { CameraConfig } from "./CameraConfig";

describe("CameraConfig", () => {
  describe("Happy Path — Rendering", () => {
    it("renders_local_camera_fields", () => {
      // Expected: Number input with value "2", dropdown shows "local"
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 2 })}
          onUpdate={vi.fn()}
        />,
      );
      const numberInput = screen.getByRole("spinbutton") as HTMLInputElement;
      expect(numberInput.value).toBe("2");
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect(select.value).toBe("local");
    });

    it("renders_rtsp_fields", () => {
      // Expected: Text input with value "rtsp://cam", dropdown shows "rtsp"
      render(
        <CameraConfig
          camera={buildRtspCamera({ rtsp_url: "rtsp://cam" })}
          onUpdate={vi.fn()}
        />,
      );
      const textInput = screen.getByRole("textbox") as HTMLInputElement;
      expect(textInput.value).toBe("rtsp://cam");
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect(select.value).toBe("rtsp");
    });

    it("renders_with_null_camera", () => {
      // Expected: Dropdown defaults to "local", device index empty, button disabled
      render(<CameraConfig camera={null} onUpdate={vi.fn()} />);
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect(select.value).toBe("local");
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).toBeDisabled();
    });
  });

  describe("State Transitions", () => {
    it("type_change_clears_fields", () => {
      // Setup: Render with local camera, change dropdown to "rtsp"
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 3 })}
          onUpdate={vi.fn()}
        />,
      );
      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "rtsp" } });
      // RTSP URL input should be empty
      const textInput = screen.getByRole("textbox") as HTMLInputElement;
      expect(textInput.value).toBe("");
    });

    it("syncs_state_when_camera_prop_changes", () => {
      // Setup: Render with local, re-render with rtsp
      const { rerender } = render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      rerender(
        <CameraConfig
          camera={buildRtspCamera({ rtsp_url: "rtsp://new" })}
          onUpdate={vi.fn()}
        />,
      );
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect(select.value).toBe("rtsp");
      const textInput = screen.getByRole("textbox") as HTMLInputElement;
      expect(textInput.value).toBe("rtsp://new");
    });

    it("updating_flag_disables_button_during_submit", async () => {
      // Setup: onUpdate returns a pending promise
      let resolveUpdate: () => void;
      const onUpdate = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            resolveUpdate = resolve;
          }),
      );
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={onUpdate}
        />,
      );
      // Make dirty
      const input = screen.getByRole("spinbutton") as HTMLInputElement;
      fireEvent.change(input, { target: { value: "5" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      fireEvent.click(button);

      // Button should show "Updating..." and be disabled
      await waitFor(() => {
        expect(button).toHaveTextContent("Updating...");
        expect(button).toBeDisabled();
      });

      // Cleanup
      await act(async () => {
        resolveUpdate!();
      });
    });

    it("updating_flag_resets_after_success", async () => {
      const onUpdate = vi.fn(() => Promise.resolve());
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={onUpdate}
        />,
      );
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "5" } });
      const button = screen.getByRole("button", { name: /update camera/i });

      await act(async () => {
        fireEvent.click(button);
      });

      expect(button).toHaveTextContent("Update Camera");
    });

    it("updating_flag_resets_after_error", async () => {
      const onUpdate = vi.fn(() => Promise.reject(new Error("fail")));
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={onUpdate}
        />,
      );
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "5" } });
      const button = screen.getByRole("button", { name: /update camera/i });

      await act(async () => {
        fireEvent.click(button);
      });

      expect(button).toHaveTextContent("Update Camera");
      // Fields retain their value
      expect((screen.getByRole("spinbutton") as HTMLInputElement).value).toBe(
        "5",
      );
    });
  });

  describe("Happy Path — Dirty Detection", () => {
    it("button_disabled_when_clean", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).toBeDisabled();
    });

    it("button_enabled_when_device_index_differs", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "3" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).not.toBeDisabled();
    });

    it("button_enabled_when_type_differs", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "rtsp" } });
      const textInput = screen.getByRole("textbox");
      fireEvent.change(textInput, { target: { value: "rtsp://x" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).not.toBeDisabled();
    });

    it("button_enabled_when_rtsp_url_differs", () => {
      render(
        <CameraConfig
          camera={buildRtspCamera({ rtsp_url: "rtsp://old" })}
          onUpdate={vi.fn()}
        />,
      );
      const textInput = screen.getByRole("textbox");
      fireEvent.change(textInput, { target: { value: "rtsp://new" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).not.toBeDisabled();
    });

    it("button_enabled_when_camera_null_and_input_provided", () => {
      render(<CameraConfig camera={null} onUpdate={vi.fn()} />);
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "0" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).not.toBeDisabled();
    });
  });

  describe("Mock / Dependency Interaction", () => {
    it("calls_on_update_with_local_config", async () => {
      const onUpdate = vi.fn(() => Promise.resolve());
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={onUpdate}
        />,
      );
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "2" } });
      const button = screen.getByRole("button", { name: /update camera/i });

      await act(async () => {
        fireEvent.click(button);
      });

      expect(onUpdate).toHaveBeenCalledWith({
        source_type: "local",
        device_index: 2,
      });
    });

    it("calls_on_update_with_rtsp_config", async () => {
      const onUpdate = vi.fn(() => Promise.resolve());
      render(
        <CameraConfig
          camera={buildRtspCamera({ rtsp_url: "rtsp://old" })}
          onUpdate={onUpdate}
        />,
      );
      const textInput = screen.getByRole("textbox");
      fireEvent.change(textInput, { target: { value: "rtsp://new" } });
      const button = screen.getByRole("button", { name: /update camera/i });

      await act(async () => {
        fireEvent.click(button);
      });

      expect(onUpdate).toHaveBeenCalledWith({
        source_type: "rtsp",
        rtsp_url: "rtsp://new",
      });
    });
  });

  describe("Boundary Values — deviceIndex", () => {
    it("non_numeric_device_index_enables_button", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "abc" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      expect(button).not.toBeDisabled();
    });

    it("submits_nan_for_non_numeric_device_index", async () => {
      const onUpdate = vi.fn(() => Promise.resolve());
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={onUpdate}
        />,
      );
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "abc" } });
      const button = screen.getByRole("button", { name: /update camera/i });

      await act(async () => {
        fireEvent.click(button);
      });

      expect(onUpdate).toHaveBeenCalledWith({
        source_type: "local",
        device_index: NaN,
      });
    });
  });

  describe("Happy Path — Styling", () => {
    it("container_has_card_style", () => {
      const { container } = render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const containerDiv = container.firstElementChild as HTMLElement;
      expect([
        "#FFFFFF",
        "#ffffff",
        "rgb(255, 255, 255)",
        "var(--color-bg-surface)",
      ]).toContain(
        containerDiv.style.backgroundColor || containerDiv.style.background,
      );
      expect([
        "1px solid #D4DAE0",
        "1px solid #d4dae0",
        "1px solid rgb(212, 218, 224)",
        "1px solid var(--color-border)",
      ]).toContain(containerDiv.style.border);
      expect(["8px", "var(--radius-md)"]).toContain(
        containerDiv.style.borderRadius,
      );
      expect(["16px", "var(--spacing-lg)"]).toContain(
        containerDiv.style.padding,
      );
      expect(containerDiv.style.display).toBe("flex");
      expect(containerDiv.style.alignItems).toBe("center");
      expect(["12px", "var(--spacing-md)"]).toContain(containerDiv.style.gap);
    });

    it("update_button_enabled_style", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      // Make dirty to enable button
      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "5" } });
      const button = screen.getByRole("button", { name: /update camera/i });
      expect([
        "#5B8CB8",
        "#5b8cb8",
        "rgb(91, 140, 184)",
        "var(--color-primary)",
      ]).toContain(button.style.backgroundColor);
      expect([
        "#FFFFFF",
        "#ffffff",
        "rgb(255, 255, 255)",
        "var(--color-white)",
      ]).toContain(button.style.color);
      expect(button.style.borderStyle).toBe("none");
      expect(["4px", "var(--radius-sm)"]).toContain(button.style.borderRadius);
      expect(button.style.cursor).toBe("pointer");
    });

    it("update_button_disabled_style", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const button = screen.getByRole("button", { name: /update camera/i });
      expect([
        "#A8C4DC",
        "#a8c4dc",
        "rgb(168, 196, 220)",
        "var(--color-primary-disabled)",
      ]).toContain(button.style.backgroundColor);
      expect(button.style.cursor).toBe("default");
    });

    it("select_has_input_style", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      expect([
        "1px solid #D4DAE0",
        "1px solid #d4dae0",
        "1px solid rgb(212, 218, 224)",
        "1px solid var(--color-border)",
      ]).toContain(select.style.border);
      expect(["4px", "var(--radius-sm)"]).toContain(select.style.borderRadius);
    });

    it("device_index_input_has_fixed_width", () => {
      render(
        <CameraConfig
          camera={buildLocalCamera({ device_index: 0 })}
          onUpdate={vi.fn()}
        />,
      );
      const input = screen.getByRole("spinbutton") as HTMLInputElement;
      expect(input.style.width).toBe("120px");
    });

    it("rtsp_input_has_flex_1", () => {
      render(
        <CameraConfig
          camera={buildRtspCamera({ rtsp_url: "rtsp://cam" })}
          onUpdate={vi.fn()}
        />,
      );
      const input = screen.getByRole("textbox") as HTMLInputElement;
      expect(["1", "1 1 0%"]).toContain(input.style.flex);
    });
  });
});
