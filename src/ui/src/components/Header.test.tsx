import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "./Header";

describe("Header", () => {
  describe("Happy Path — Rendering", () => {
    it("renders_header_element", () => {
      // Setup: Render <Header />
      // Expected: A <header> element is present in the document
      const { container } = render(<Header />);
      const headerEl = container.querySelector("header");
      expect(headerEl).toBeInTheDocument();
    });

    it("displays_model_lens_title", () => {
      // Setup: Render <Header />
      // Expected: An <h1> element containing the text "ModelLens" is present
      render(<Header />);
      const h1 = screen.getByRole("heading", { level: 1 });
      expect(h1).toHaveTextContent("ModelLens");
    });

    it("renders_identically_on_rerender", () => {
      // Setup: Render <Header /> twice
      // Expected: Both render results produce identical DOM structure
      const { container: first } = render(<Header />);
      const { container: second } = render(<Header />);
      expect(first.innerHTML).toEqual(second.innerHTML);
    });
  });

  describe("Happy Path — Styling", () => {
    it("header_has_surface_background", () => {
      const { container } = render(<Header />);
      const headerEl = container.querySelector("header") as HTMLElement;
      // jsdom normalizes hex to rgb; accept multiple representations
      const bg = headerEl.style.backgroundColor || headerEl.style.background;
      expect([
        "#FFFFFF",
        "#ffffff",
        "rgb(255, 255, 255)",
        "var(--color-bg-surface)",
      ]).toContain(bg);
    });

    it("header_has_bottom_border", () => {
      const { container } = render(<Header />);
      const headerEl = container.querySelector("header") as HTMLElement;
      const borderBottom = headerEl.style.borderBottom;
      expect([
        "1px solid #D4DAE0",
        "1px solid #d4dae0",
        "1px solid rgb(212, 218, 224)",
        "1px solid var(--color-border)",
      ]).toContain(borderBottom);
    });

    it("header_has_correct_padding", () => {
      const { container } = render(<Header />);
      const headerEl = container.querySelector("header") as HTMLElement;
      const padding = headerEl.style.padding;
      expect(["12px 24px", "var(--spacing-md) var(--spacing-xl)"]).toContain(
        padding,
      );
    });

    it("h1_has_correct_style", () => {
      render(<Header />);
      const h1 = screen.getByRole("heading", { level: 1 }) as HTMLElement;
      // jsdom may normalize "0" to "0px"
      expect(["0", "0px"]).toContain(h1.style.margin);
      expect([
        "#2C3E50",
        "#2c3e50",
        "rgb(44, 62, 80)",
        "var(--color-text-primary)",
      ]).toContain(h1.style.color);
      expect(["1.5rem", "var(--font-size-heading)"]).toContain(
        h1.style.fontSize,
      );
      expect(h1.style.fontWeight).toBe("bold");
    });
  });
});
