import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TargetLabels from "../../../src/ui/src/components/TargetLabels";

describe("TargetLabels", () => {
  const validLabels = ["cat", "car", "dog", "person"];
  const activeLabels = ["cat", "dog"];
  let onUpdate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onUpdate = vi.fn(() => Promise.resolve());
  });

  // Helper to open the dropdown
  async function openDropdown(user: ReturnType<typeof userEvent.setup>) {
    const trigger = screen.getByRole("button", { name: /labels selected|no labels/i });
    await user.click(trigger);
  }

  // 1.1 Happy Path — Rendering

  it("test_target_labels_trigger_shows_count", () => {
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );
    expect(screen.getByText("2 labels selected")).toBeInTheDocument();
  });

  it("test_target_labels_trigger_shows_none_selected", () => {
    render(
      <TargetLabels validLabels={validLabels} activeLabels={[]} onUpdate={onUpdate} />,
    );
    expect(screen.getByText("No labels selected")).toBeInTheDocument();
  });

  it("test_target_labels_trigger_shows_all_selected", () => {
    render(
      <TargetLabels
        validLabels={["cat", "dog"]}
        activeLabels={["cat", "dog"]}
        onUpdate={onUpdate}
      />,
    );
    expect(screen.getByText("All labels selected")).toBeInTheDocument();
  });

  it("test_target_labels_dropdown_closed_by_default", () => {
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );
    expect(screen.queryByPlaceholderText("Search labels...")).not.toBeInTheDocument();
  });

  // 1.2 Happy Path — Dropdown Interaction

  it("test_target_labels_click_trigger_opens_dropdown", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);

    expect(screen.getByPlaceholderText("Search labels...")).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox").length).toBe(validLabels.length);
  });

  it("test_target_labels_click_trigger_again_closes_dropdown", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await openDropdown(user);

    expect(screen.queryByPlaceholderText("Search labels...")).not.toBeInTheDocument();
  });

  it("test_target_labels_click_outside_closes_dropdown", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <div data-testid="outside">outside</div>
        <TargetLabels
          validLabels={validLabels}
          activeLabels={activeLabels}
          onUpdate={onUpdate}
        />
      </div>,
    );

    await openDropdown(user);
    await user.click(screen.getByTestId("outside"));

    expect(screen.queryByPlaceholderText("Search labels...")).not.toBeInTheDocument();
  });

  it("test_target_labels_active_labels_pre_checked", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const catCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("cat"),
    );
    const dogCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("dog"),
    );
    expect(catCheckbox?.checked).toBe(true);
    expect(dogCheckbox?.checked).toBe(false);
  });

  it("test_target_labels_toggle_label_on", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const dogCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("dog"),
    )!;
    await user.click(dogCheckbox);

    expect(dogCheckbox.checked).toBe(true);
  });

  it("test_target_labels_toggle_label_off", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const catCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("cat"),
    )!;
    await user.click(catCheckbox);

    expect(catCheckbox.checked).toBe(false);
  });

  // 1.3 Happy Path — Select All / Clear All

  it("test_target_labels_select_all", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.click(screen.getByRole("button", { name: /select all/i }));

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes.every((cb) => cb.checked)).toBe(true);
  });

  it("test_target_labels_clear_all", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.click(screen.getByRole("button", { name: /clear all/i }));

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes.every((cb) => !cb.checked)).toBe(true);
  });

  it("test_target_labels_select_all_ignores_search_filter", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels validLabels={validLabels} activeLabels={[]} onUpdate={onUpdate} />,
    );

    await openDropdown(user);
    await user.type(screen.getByPlaceholderText("Search labels..."), "cat");
    await user.click(screen.getByRole("button", { name: /select all/i }));

    // Clear search to reveal all checkboxes
    await user.clear(screen.getByPlaceholderText("Search labels..."));

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes.length).toBe(validLabels.length);
    expect(checkboxes.every((cb) => cb.checked)).toBe(true);
  });

  // 1.4 Happy Path — Search

  it("test_target_labels_search_filters_list", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.type(screen.getByPlaceholderText("Search labels..."), "ca");

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBe(2); // "cat" and "car"
    expect(screen.getByText("cat")).toBeInTheDocument();
    expect(screen.getByText("car")).toBeInTheDocument();
    expect(screen.queryByText("dog")).not.toBeInTheDocument();
  });

  it("test_target_labels_search_case_insensitive", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.type(screen.getByPlaceholderText("Search labels..."), "CAT");

    expect(screen.getByText("cat")).toBeInTheDocument();
  });

  it("test_target_labels_search_no_match", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.type(screen.getByPlaceholderText("Search labels..."), "zzz");

    expect(screen.queryAllByRole("checkbox").length).toBe(0);
  });

  it("test_target_labels_clear_search_restores_list", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const searchInput = screen.getByPlaceholderText("Search labels...");
    await user.type(searchInput, "ca");
    await user.clear(searchInput);

    expect(screen.getAllByRole("checkbox").length).toBe(validLabels.length);
  });

  // 1.5 Happy Path — Update Submission

  it("test_target_labels_update_calls_on_update", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const personCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("person"),
    )!;
    await user.click(personCheckbox);
    await user.click(screen.getByRole("button", { name: /update labels/i }));

    expect(onUpdate).toHaveBeenCalledTimes(1);
    const calledWith = onUpdate.mock.calls[0][0] as string[];
    expect(calledWith.sort()).toEqual(["cat", "person"].sort());
  });

  it("test_target_labels_update_button_shows_loading", async () => {
    const user = userEvent.setup();
    let resolveUpdate!: () => void;
    onUpdate.mockReturnValue(new Promise<void>((r) => (resolveUpdate = r)));

    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const dogCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("dog"),
    )!;
    await user.click(dogCheckbox);
    await user.click(screen.getByRole("button", { name: /update labels/i }));

    const button = screen.getByRole("button", { name: /updating/i });
    expect(button).toBeDisabled();

    resolveUpdate();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /update labels/i })).toBeInTheDocument();
    });
  });

  it("test_target_labels_update_success_resyncs", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const dogCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("dog"),
    )!;
    await user.click(dogCheckbox);
    await user.click(screen.getByRole("button", { name: /update labels/i }));

    rerender(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat", "dog"]}
        onUpdate={onUpdate}
      />,
    );

    expect(screen.getByText("2 labels selected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /update labels/i })).toBeDisabled();
  });

  it("test_target_labels_update_failure_preserves_selection", async () => {
    const user = userEvent.setup();
    onUpdate.mockRejectedValue(new Error("update failed"));

    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const dogCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("dog"),
    )!;
    await user.click(dogCheckbox);
    await user.click(screen.getByRole("button", { name: /update labels/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /update labels/i })).toBeEnabled();
    });
    expect(dogCheckbox.checked).toBe(true);
  });

  // 1.6 Dirty Detection

  it("test_target_labels_button_disabled_when_clean", () => {
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );
    expect(screen.getByRole("button", { name: /update labels/i })).toBeDisabled();
  });

  it("test_target_labels_button_enabled_when_label_toggled", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const personCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("person"),
    )!;
    await user.click(personCheckbox);

    expect(screen.getByRole("button", { name: /update labels/i })).toBeEnabled();
  });

  it("test_target_labels_button_disabled_when_reverted", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={activeLabels}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const personCheckbox = checkboxes.find(
      (cb) => cb.closest("label")?.textContent?.includes("person"),
    )!;
    await user.click(personCheckbox);
    await user.click(personCheckbox);

    expect(screen.getByRole("button", { name: /update labels/i })).toBeDisabled();
  });

  it("test_target_labels_button_enabled_after_select_all", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.click(screen.getByRole("button", { name: /select all/i }));

    expect(screen.getByRole("button", { name: /update labels/i })).toBeEnabled();
  });

  it("test_target_labels_button_enabled_after_clear_all", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels
        validLabels={validLabels}
        activeLabels={["cat"]}
        onUpdate={onUpdate}
      />,
    );

    await openDropdown(user);
    await user.click(screen.getByRole("button", { name: /clear all/i }));

    expect(screen.getByRole("button", { name: /update labels/i })).toBeEnabled();
  });

  // 1.7 None / Empty Input

  it("test_target_labels_empty_valid_labels", async () => {
    const user = userEvent.setup();
    render(<TargetLabels validLabels={[]} activeLabels={[]} onUpdate={onUpdate} />);

    await openDropdown(user);

    expect(screen.getByPlaceholderText("Search labels...")).toBeInTheDocument();
    expect(screen.queryAllByRole("checkbox").length).toBe(0);
  });

  it("test_target_labels_empty_active_labels", async () => {
    const user = userEvent.setup();
    render(
      <TargetLabels validLabels={validLabels} activeLabels={[]} onUpdate={onUpdate} />,
    );

    await openDropdown(user);

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes.every((cb) => !cb.checked)).toBe(true);
  });
});
