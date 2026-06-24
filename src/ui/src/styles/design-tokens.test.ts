import { describe, it, expect } from "vitest";
import { parseRootTokens } from "../test-helpers/style-assertions";

/**
 * Test Specification: design-tokens.test.ts
 *
 * Source: src/ui/src/styles/design-tokens.css
 *
 * Tests verify that the CSS file defines all required design tokens
 * on the :root selector with the correct values.
 *
 * SCAFFOLDED: This test requires the production file
 * `src/ui/src/styles/design-tokens.css` to exist. All 28 test rows
 * are blocked until the CSS file is created. Once available, Vite's
 * ?raw import will inline the text for parsing.
 */

// Import the CSS file as raw text via Vite's ?raw suffix.
// Missing production surface: src/ui/src/styles/design-tokens.css
// @ts-ignore — file may not exist yet; Vite will error until created
import cssText from "./design-tokens.css?raw";

describe("DesignTokens", () => {
  describe("Happy Path — Token Definitions", () => {
    let tokens: Map<string, string>;

    // Parse the :root block once for all token tests
    tokens = parseRootTokens(cssText as string);

    it("defines_color_bg_page", () => {
      expect(tokens.get("--color-bg-page")).toBe("#F5F6F8");
    });

    it("defines_color_bg_surface", () => {
      expect(tokens.get("--color-bg-surface")).toBe("#FFFFFF");
    });

    it("defines_color_bg_canvas_idle", () => {
      expect(tokens.get("--color-bg-canvas-idle")).toBe("#FFFFFF");
    });

    it("defines_color_text_primary", () => {
      expect(tokens.get("--color-text-primary")).toBe("#2C3E50");
    });

    it("defines_color_text_muted", () => {
      expect(tokens.get("--color-text-muted")).toBe("#6B7B8D");
    });

    it("defines_color_border", () => {
      expect(tokens.get("--color-border")).toBe("#D4DAE0");
    });

    it("defines_color_primary", () => {
      expect(tokens.get("--color-primary")).toBe("#5B8CB8");
    });

    it("defines_color_primary_disabled", () => {
      expect(tokens.get("--color-primary-disabled")).toBe("#A8C4DC");
    });

    it("defines_color_secondary", () => {
      expect(tokens.get("--color-secondary")).toBe("#6B7B8D");
    });

    it("defines_color_secondary_disabled", () => {
      expect(tokens.get("--color-secondary-disabled")).toBe("#D4DAE0");
    });

    it("defines_color_white", () => {
      expect(tokens.get("--color-white")).toBe("#FFFFFF");
    });

    it("defines_font_family", () => {
      expect(tokens.get("--font-family")).toBe(
        "system-ui, -apple-system, sans-serif",
      );
    });

    it("defines_font_size_heading", () => {
      expect(tokens.get("--font-size-heading")).toBe("1.5rem");
    });

    it("defines_font_size_body", () => {
      expect(tokens.get("--font-size-body")).toBe("1.1rem");
    });

    it("defines_font_size_small", () => {
      expect(tokens.get("--font-size-small")).toBe("0.85rem");
    });

    it("defines_font_size_caption", () => {
      expect(tokens.get("--font-size-caption")).toBe("0.8rem");
    });

    it("defines_font_size_canvas_label", () => {
      expect(tokens.get("--font-size-canvas-label")).toBe("14px");
    });

    it("defines_spacing_xs", () => {
      expect(tokens.get("--spacing-xs")).toBe("4px");
    });

    it("defines_spacing_sm", () => {
      expect(tokens.get("--spacing-sm")).toBe("8px");
    });

    it("defines_spacing_md", () => {
      expect(tokens.get("--spacing-md")).toBe("12px");
    });

    it("defines_spacing_lg", () => {
      expect(tokens.get("--spacing-lg")).toBe("16px");
    });

    it("defines_spacing_xl", () => {
      expect(tokens.get("--spacing-xl")).toBe("24px");
    });

    it("defines_radius_sm", () => {
      expect(tokens.get("--radius-sm")).toBe("4px");
    });

    it("defines_radius_md", () => {
      expect(tokens.get("--radius-md")).toBe("8px");
    });

    it("defines_canvas_width", () => {
      expect(tokens.get("--canvas-width")).toBe("800");
    });

    it("defines_canvas_height", () => {
      expect(tokens.get("--canvas-height")).toBe("450");
    });

    it("defines_canvas_aspect", () => {
      expect(tokens.get("--canvas-aspect")).toBe("16/9");
    });

    it("defines_dropdown_max_height", () => {
      expect(tokens.get("--dropdown-max-height")).toBe("300px");
    });

    it("defines_dropdown_list_max_height", () => {
      expect(tokens.get("--dropdown-list-max-height")).toBe("220px");
    });
  });
});
