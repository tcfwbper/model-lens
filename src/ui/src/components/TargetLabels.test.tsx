import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

/**
 * Test Specification: TargetLabels.test.tsx
 *
 * Source: src/ui/src/components/TargetLabels.tsx
 */

import { TargetLabels } from "./TargetLabels";
import type { TargetLabelsProps } from "./TargetLabels";

// --- Helpers ---

function renderTargetLabels(props: Partial<TargetLabelsProps> = {}) {
  const defaultProps: TargetLabelsProps = {
    validLabels: ["cat", "dog"],
    activeLabels: ["cat"],
    onUpdate: vi.fn(() => Promise.resolve()),
    ...props,
  };
  return render(<TargetLabels {...defaultProps} />);
}

function openDropdown() {
  // Click the trigger button to open dropdown
  const trigger = screen.getByRole("button", { name: /labels selected|No labels selected|All labels selected/i });
  fireEvent.click(trigger);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TargetLabels", () => {
  describe("Happy Path — Rendering", () => {
    it("renders_trigger_button_with_count", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog", "bird"],
        activeLabels: ["cat", "dog"],
      });
      expect(screen.getByText("2 labels selected")).toBeInTheDocument();
    });

    it("renders_no_labels_selected_text", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: [],
      });
      expect(screen.getByText("No labels selected")).toBeInTheDocument();
    });

    it("renders_all_labels_selected_text", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat", "dog"],
      });
      expect(screen.getByText("All labels selected")).toBeInTheDocument();
    });

    it("dropdown_hidden_initially", () => {
      renderTargetLabels();
      // No checkboxes should be visible
      expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    });

    it("dropdown_opens_on_trigger_click", () => {
      renderTargetLabels();
      openDropdown();
      // Checkboxes should now be visible
      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBeGreaterThan(0);
    });
  });

  describe("State Transitions", () => {
    it("toggle_label_selection", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog", "bird"],
        activeLabels: ["cat"],
      });
      openDropdown();
      const dogCheckbox = screen.getByLabelText("dog");
      fireEvent.click(dogCheckbox);
      expect(screen.getByText("2 labels selected")).toBeInTheDocument();
    });

    it("deselect_label", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat", "dog"],
      });
      openDropdown();
      const catCheckbox = screen.getByLabelText("cat");
      fireEvent.click(catCheckbox);
      expect(screen.getByText("1 labels selected")).toBeInTheDocument();
    });

    it("select_all_selects_all_valid_labels", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog", "bird"],
        activeLabels: [],
      });
      openDropdown();
      // Type in search to filter, then click Select All
      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "cat" } });
      const selectAll = screen.getByRole("button", { name: /select all/i });
      fireEvent.click(selectAll);
      // All labels should be selected (not just filtered ones)
      expect(screen.getByText("All labels selected")).toBeInTheDocument();
    });

    it("clear_all_deselects_everything", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat", "dog"],
      });
      openDropdown();
      const clearAll = screen.getByRole("button", { name: /clear all/i });
      fireEvent.click(clearAll);
      expect(screen.getByText("No labels selected")).toBeInTheDocument();
    });

    it("syncs_selected_when_active_labels_change", () => {
      const { rerender } = render(
        <TargetLabels
          validLabels={["cat", "dog"]}
          activeLabels={["cat"]}
          onUpdate={vi.fn(() => Promise.resolve())}
        />
      );
      rerender(
        <TargetLabels
          validLabels={["cat", "dog"]}
          activeLabels={["dog"]}
          onUpdate={vi.fn(() => Promise.resolve())}
        />
      );
      // Trigger should now show 1 label selected — "dog" only
      expect(screen.getByText("1 labels selected")).toBeInTheDocument();
    });

    it("dropdown_closes_on_click_outside", () => {
      renderTargetLabels();
      openDropdown();
      // Verify dropdown is open
      expect(screen.getAllByRole("checkbox").length).toBeGreaterThan(0);
      // Click outside (on document body)
      fireEvent.mouseDown(document.body);
      // Dropdown should close — no checkboxes visible
      expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    });

    it("updating_flag_disables_button_during_submit", async () => {
      let resolveUpdate: () => void;
      const onUpdate = vi.fn(
        () => new Promise<void>((resolve) => { resolveUpdate = resolve; })
      );
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat"],
        onUpdate,
      });
      openDropdown();
      // Toggle "dog" to make dirty
      fireEvent.click(screen.getByLabelText("dog"));
      const updateBtn = screen.getByRole("button", { name: /update labels/i });
      fireEvent.click(updateBtn);

      await waitFor(() => {
        expect(updateBtn).toHaveTextContent("Updating...");
        expect(updateBtn).toBeDisabled();
      });

      // Cleanup
      await act(async () => { resolveUpdate!(); });
    });

    it("updating_flag_resets_after_success", async () => {
      const onUpdate = vi.fn(() => Promise.resolve());
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat"],
        onUpdate,
      });
      openDropdown();
      fireEvent.click(screen.getByLabelText("dog"));
      const updateBtn = screen.getByRole("button", { name: /update labels/i });

      await act(async () => {
        fireEvent.click(updateBtn);
      });

      expect(updateBtn).toHaveTextContent("Update Labels");
    });

    it("updating_flag_resets_after_error", async () => {
      const onUpdate = vi.fn(() => Promise.reject(new Error("fail")));
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat"],
        onUpdate,
      });
      openDropdown();
      fireEvent.click(screen.getByLabelText("dog"));
      const updateBtn = screen.getByRole("button", { name: /update labels/i });

      await act(async () => {
        fireEvent.click(updateBtn);
      });

      expect(updateBtn).toHaveTextContent("Update Labels");
      // Selection still includes "dog"
      openDropdown();
      const dogCheckbox = screen.getByLabelText("dog") as HTMLInputElement;
      expect(dogCheckbox.checked).toBe(true);
    });
  });

  describe("Happy Path — Dirty Detection", () => {
    it("update_button_disabled_when_clean", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat"],
      });
      const updateBtn = screen.getByRole("button", { name: /update labels/i });
      expect(updateBtn).toBeDisabled();
    });

    it("update_button_enabled_when_dirty", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat"],
      });
      openDropdown();
      fireEvent.click(screen.getByLabelText("dog"));
      const updateBtn = screen.getByRole("button", { name: /update labels/i });
      expect(updateBtn).not.toBeDisabled();
    });
  });

  describe("Happy Path — Search Filtering", () => {
    it("filters_labels_by_search_term", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog", "catfish"],
        activeLabels: [],
      });
      openDropdown();
      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "cat" } });
      // Only "cat" and "catfish" should be visible
      expect(screen.getByLabelText("cat")).toBeInTheDocument();
      expect(screen.getByLabelText("catfish")).toBeInTheDocument();
      expect(screen.queryByLabelText("dog")).not.toBeInTheDocument();
    });

    it("empty_search_shows_all_labels", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: [],
      });
      openDropdown();
      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "cat" } });
      fireEvent.change(searchInput, { target: { value: "" } });
      expect(screen.getByLabelText("cat")).toBeInTheDocument();
      expect(screen.getByLabelText("dog")).toBeInTheDocument();
    });

    it("search_filters_out_all_labels", () => {
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: [],
      });
      openDropdown();
      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: "xyz" } });
      expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    });
  });

  describe("Mock / Dependency Interaction", () => {
    it("calls_on_update_with_selected_labels", async () => {
      const onUpdate = vi.fn(() => Promise.resolve());
      renderTargetLabels({
        validLabels: ["cat", "dog"],
        activeLabels: ["cat"],
        onUpdate,
      });
      openDropdown();
      fireEvent.click(screen.getByLabelText("dog"));
      const updateBtn = screen.getByRole("button", { name: /update labels/i });

      await act(async () => {
        fireEvent.click(updateBtn);
      });

      expect(onUpdate).toHaveBeenCalledTimes(1);
      const calledWith = onUpdate.mock.calls[0][0] as string[];
      expect(calledWith.sort()).toEqual(["cat", "dog"]);
    });
  });

  describe("Null / Empty Input", () => {
    it("empty_valid_labels_renders_no_checkboxes", () => {
      renderTargetLabels({
        validLabels: [],
        activeLabels: [],
      });
      expect(screen.getByText("No labels selected")).toBeInTheDocument();
      openDropdown();
      expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    });

    it("select_all_with_empty_valid_labels", () => {
      renderTargetLabels({
        validLabels: [],
        activeLabels: [],
      });
      openDropdown();
      const selectAll = screen.getByRole("button", { name: /select all/i });
      fireEvent.click(selectAll);
      // Selection remains empty, button stays disabled
      const updateBtn = screen.getByRole("button", { name: /update labels/i });
      expect(updateBtn).toBeDisabled();
    });
  });
});
