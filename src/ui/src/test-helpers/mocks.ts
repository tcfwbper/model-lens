/**
 * Shared mock factories and helpers for UI test suites.
 * Provides mock objects for hooks, EventSource, Image, canvas context, and fetch.
 */
import { vi } from "vitest";
import type { RuntimeConfig, CameraConfigData, FrameData } from "./fixtures";

// --- useConfig mock return type ---

export interface UseConfigReturn {
  runtimeConfig: RuntimeConfig | null;
  validLabels: string[];
  loading: boolean;
  updateCamera: ReturnType<typeof vi.fn>;
  updateLabels: ReturnType<typeof vi.fn>;
}

export function buildUseConfigReturn(
  overrides: Partial<UseConfigReturn> = {}
): UseConfigReturn {
  return {
    runtimeConfig: null,
    validLabels: [],
    loading: false,
    updateCamera: vi.fn(),
    updateLabels: vi.fn(),
    ...overrides,
  };
}

// --- useStream mock return type ---

export interface UseStreamReturn {
  frame: FrameData | null;
}

export function buildUseStreamReturn(
  overrides: Partial<UseStreamReturn> = {}
): UseStreamReturn {
  return {
    frame: null,
    ...overrides,
  };
}

// --- Mock EventSource ---

export interface MockEventSource {
  url: string;
  close: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  listeners: Record<string, Array<(event: unknown) => void>>;
  simulateMessage: (data: string) => void;
  simulateError: () => void;
}

export function createMockEventSourceClass(): {
  MockClass: new (url: string) => MockEventSource;
  instances: MockEventSource[];
} {
  const instances: MockEventSource[] = [];

  class MockClass {
    url: string;
    close = vi.fn();
    addEventListener = vi.fn(
      (event: string, handler: (event: unknown) => void) => {
        if (!this.listeners[event]) {
          this.listeners[event] = [];
        }
        this.listeners[event].push(handler);
      }
    );
    removeEventListener = vi.fn();
    listeners: Record<string, Array<(event: unknown) => void>> = {};

    simulateMessage(data: string) {
      const handlers = this.listeners["message"] || [];
      handlers.forEach((h) => h({ data }));
    }

    simulateError() {
      const handlers = this.listeners["error"] || [];
      handlers.forEach((h) => h(new Event("error")));
    }

    constructor(url: string) {
      this.url = url;
      instances.push(this as unknown as MockEventSource);
    }
  }

  return {
    MockClass: MockClass as unknown as new (url: string) => MockEventSource,
    instances,
  };
}

// --- Mock Canvas 2D Context ---

export interface MockCanvas2DContext {
  clearRect: ReturnType<typeof vi.fn>;
  drawImage: ReturnType<typeof vi.fn>;
  strokeRect: ReturnType<typeof vi.fn>;
  fillRect: ReturnType<typeof vi.fn>;
  fillText: ReturnType<typeof vi.fn>;
  measureText: ReturnType<typeof vi.fn>;
  beginPath: ReturnType<typeof vi.fn>;
  stroke: ReturnType<typeof vi.fn>;
  save: ReturnType<typeof vi.fn>;
  restore: ReturnType<typeof vi.fn>;
  lineWidth: number;
  strokeStyle: string;
  fillStyle: string;
  font: string;
}

export function createMockCanvas2DContext(): MockCanvas2DContext {
  return {
    clearRect: vi.fn(),
    drawImage: vi.fn(),
    strokeRect: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    measureText: vi.fn(() => ({ width: 50 })),
    beginPath: vi.fn(),
    stroke: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    lineWidth: 0,
    strokeStyle: "",
    fillStyle: "",
    font: "",
  };
}

// --- Mock Image ---

export interface MockImage {
  src: string;
  onload: (() => void) | null;
  complete: boolean;
  width: number;
  height: number;
}

export function setupMockImage(opts: { fireOnloadSync?: boolean } = {}): {
  instances: MockImage[];
  restore: () => void;
} {
  const instances: MockImage[] = [];
  const OriginalImage = globalThis.Image;

  class FakeImage {
    src = "";
    onload: (() => void) | null = null;
    complete = false;
    width = 800;
    height = 450;

    constructor() {
      instances.push(this as unknown as MockImage);
      if (opts.fireOnloadSync) {
        // Use a getter to fire onload when src is set
        const self = this;
        Object.defineProperty(this, "src", {
          set(value: string) {
            self.complete = true;
            // Fire onload synchronously after microtask
            if (self.onload) {
              self.onload();
            }
          },
          get() {
            return "";
          },
        });
      }
    }
  }

  globalThis.Image = FakeImage as unknown as typeof Image;

  return {
    instances,
    restore: () => {
      globalThis.Image = OriginalImage;
    },
  };
}

// --- Mock Fetch ---

export interface FetchMockConfig {
  url: string;
  response?: {
    ok: boolean;
    status: number;
    json?: () => Promise<unknown>;
    text?: () => Promise<string>;
  };
  error?: Error;
}

export function createMockFetch(configs: FetchMockConfig[]): ReturnType<typeof vi.fn> {
  return vi.fn((url: string, _opts?: RequestInit) => {
    const config = configs.find((c) => url.includes(c.url));
    if (!config) {
      return Promise.reject(new TypeError("Failed to fetch"));
    }
    if (config.error) {
      return Promise.reject(config.error);
    }
    const resp = config.response!;
    return Promise.resolve({
      ok: resp.ok,
      status: resp.status,
      json: resp.json || (() => Promise.resolve({})),
      text: resp.text || (() => Promise.resolve("")),
    });
  });
}
