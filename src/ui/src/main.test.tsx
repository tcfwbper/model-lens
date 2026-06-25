import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * Test Specification: main.test.tsx
 *
 * Source: src/ui/src/main.tsx
 *
 * Tests the application entry point which executes as a side-effect module.
 * Each test resets the module registry and dynamically imports main.tsx to
 * trigger its side-effect execution in isolation.
 */

// --- Shared spies ---

const mockRender = vi.fn();
const mockCreateRoot = vi.fn((container: unknown) => {
  if (container === null || container === undefined) {
    throw new TypeError(
      "createRoot(...): Target container is not a DOM element.",
    );
  }
  return { render: mockRender };
});

/**
 * Tracks whether the design-tokens.css mock was resolved during module import.
 * Reset in beforeEach so each test gets an isolated observation.
 */
let designTokensCssImported = false;

vi.mock("react-dom/client", () => ({
  createRoot: (...args: unknown[]) => mockCreateRoot(...args),
}));

vi.mock("./App.tsx", () => ({
  default: function MockApp() {
    return null;
  },
}));

vi.mock("./styles/design-tokens.css", () => {
  designTokensCssImported = true;
  return {};
});

beforeEach(() => {
  // Reset call counts and tracking flags between tests
  mockCreateRoot.mockClear();
  mockRender.mockClear();
  designTokensCssImported = false;

  // Reset module registry so main.tsx re-executes on each import
  vi.resetModules();

  // Re-register mocks after resetModules so they apply to fresh imports
  vi.mock("react-dom/client", () => ({
    createRoot: (...args: unknown[]) => mockCreateRoot(...args),
  }));
  vi.mock("./App.tsx", () => ({
    default: function MockApp() {
      return null;
    },
  }));
  vi.mock("./styles/design-tokens.css", () => {
    designTokensCssImported = true;
    return {};
  });
});

afterEach(() => {
  // Clean up any #root element added during tests
  const rootEl = document.getElementById("root");
  if (rootEl) {
    document.body.removeChild(rootEl);
  }
});

/** Helper: create and attach a #root element to document.body */
function createRootElement(): HTMLElement {
  const el = document.createElement("div");
  el.id = "root";
  document.body.appendChild(el);
  return el;
}

/** Helper: dynamically import main.tsx to trigger its side-effect */
async function importMain(): Promise<void> {
  await import("./main.tsx");
}

describe("main", () => {
  describe("Happy Path — Rendering", () => {
    it("renders_app_inside_strict_mode", async () => {
      createRootElement();
      await importMain();

      expect(mockCreateRoot).toHaveBeenCalledTimes(1);
      expect(mockRender).toHaveBeenCalledTimes(1);

      const renderedTree = mockRender.mock.calls[0][0];
      // StrictMode is represented as a Symbol in React
      expect(renderedTree.type).toBe(Symbol.for("react.strict_mode"));
      // The child of StrictMode should be the App mock component
      const appChild = renderedTree.props.children;
      expect(appChild).toBeDefined();
      expect(appChild.type).toBeDefined();
      // Verify it's a function (the MockApp component)
      expect(typeof appChild.type).toBe("function");
    });

    it("calls_create_root_with_root_element", async () => {
      const rootEl = createRootElement();
      await importMain();

      expect(mockCreateRoot).toHaveBeenCalledTimes(1);
      expect(mockCreateRoot).toHaveBeenCalledWith(rootEl);
    });
  });

  describe("Mock / Dependency Interaction", () => {
    it("does_not_pass_props_to_app", async () => {
      createRootElement();
      await importMain();

      const renderedTree = mockRender.mock.calls[0][0];
      // Navigate to App within StrictMode children
      const appElement = renderedTree.props.children;
      // App should be rendered with no props (empty object aside from internal keys)
      const appProps = { ...appElement.props };
      // Remove React internal keys if any
      delete appProps.children;
      expect(Object.keys(appProps)).toHaveLength(0);
    });

    it("create_root_called_only_once", async () => {
      createRootElement();
      await importMain();

      expect(mockCreateRoot).toHaveBeenCalledTimes(1);
    });
  });

  describe("Edge Cases", () => {
    it("throws_when_root_element_missing", async () => {
      // Do NOT create a #root element — document.getElementById("root") returns null
      // The non-null assertion (!) in createRoot(document.getElementById("root")!)
      // passes null to createRoot, which should throw a TypeError
      await expect(importMain()).rejects.toThrow();
    });
  });
});
