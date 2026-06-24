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
});
