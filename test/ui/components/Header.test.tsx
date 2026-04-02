import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Header from "../../../src/ui/src/components/Header";

describe("Header", () => {
  it("test_header_renders_app_title", () => {
    render(<Header />);
    expect(screen.getByText("ModelLens")).toBeInTheDocument();
  });

  it("test_header_renders_as_heading", () => {
    render(<Header />);
    const heading = screen.getByRole("heading");
    expect(heading).toHaveTextContent("ModelLens");
  });
});
