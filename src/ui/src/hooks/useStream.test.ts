import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { createMockEventSourceClass } from "../test-helpers/mocks";
import type { MockEventSource } from "../test-helpers/mocks";

/**
 * Test Specification: useStream.test.ts
 *
 * Source: src/ui/src/hooks/useStream.ts
 */

import { useStream } from "./useStream";

let mockEventSourceClass: ReturnType<typeof createMockEventSourceClass>;
let instances: MockEventSource[];

beforeEach(() => {
  mockEventSourceClass = createMockEventSourceClass();
  instances = mockEventSourceClass.instances;
  (globalThis as unknown as { EventSource: unknown }).EventSource =
    mockEventSourceClass.MockClass;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useStream", () => {
  describe("Happy Path — Connection Lifecycle", () => {
    it("opens_event_source_when_active_true", () => {
      // Expected: new EventSource("/stream") called
      renderHook(() => useStream(true));
      expect(instances.length).toBe(1);
      expect(instances[0].url).toBe("/stream");
    });

    it("closes_event_source_when_active_false", () => {
      // Setup: Render with active=true, then re-render with active=false
      // Expected: close() called on the EventSource instance
      const { rerender } = renderHook(
        ({ active }) => useStream(active),
        { initialProps: { active: true } }
      );
      const instance = instances[0];
      rerender({ active: false });
      expect(instance.close).toHaveBeenCalled();
    });

    it("no_event_source_when_initially_inactive", () => {
      // Expected: EventSource constructor never called
      renderHook(() => useStream(false));
      expect(instances.length).toBe(0);
    });

    it("closes_event_source_on_unmount", () => {
      // Expected: close() called on unmount
      const { unmount } = renderHook(() => useStream(true));
      const instance = instances[0];
      unmount();
      expect(instance.close).toHaveBeenCalled();
    });

    it("rapid_toggle_closes_before_reopening", () => {
      // Setup: Render with active=true, then false, then true
      // Expected: First instance closed, second created
      const { rerender } = renderHook(
        ({ active }) => useStream(active),
        { initialProps: { active: true } }
      );
      const first = instances[0];
      rerender({ active: false });
      rerender({ active: true });
      expect(first.close).toHaveBeenCalled();
      expect(instances.length).toBe(2);
    });
  });

  describe("Happy Path — Frame Processing", () => {
    it("parses_frame_from_message_event", () => {
      // Expected: frame equals parsed JSON data
      const { result } = renderHook(() => useStream(true));
      const frameJson = JSON.stringify({
        jpeg_b64: "abc",
        timestamp: 1,
        source: "cam",
        detections: [],
      });
      act(() => {
        instances[0].simulateMessage(frameJson);
      });
      expect(result.current.frame).toEqual({
        jpeg_b64: "abc",
        timestamp: 1,
        source: "cam",
        detections: [],
      });
    });

    it("replaces_frame_on_new_message", () => {
      // Expected: frame equals second message data
      const { result } = renderHook(() => useStream(true));
      act(() => {
        instances[0].simulateMessage(
          JSON.stringify({ jpeg_b64: "first", timestamp: 1, source: "a", detections: [] })
        );
      });
      act(() => {
        instances[0].simulateMessage(
          JSON.stringify({ jpeg_b64: "second", timestamp: 2, source: "b", detections: [] })
        );
      });
      expect(result.current.frame).toEqual({
        jpeg_b64: "second",
        timestamp: 2,
        source: "b",
        detections: [],
      });
    });
  });

  describe("State Transitions", () => {
    it("frame_null_when_inactive", () => {
      // Expected: frame is null
      const { result } = renderHook(() => useStream(false));
      expect(result.current.frame).toBeNull();
    });

    it("frame_reset_to_null_on_deactivation", () => {
      // Setup: active=true, simulate message, then set active=false
      const { result, rerender } = renderHook(
        ({ active }) => useStream(active),
        { initialProps: { active: true } }
      );
      act(() => {
        instances[0].simulateMessage(
          JSON.stringify({ jpeg_b64: "x", timestamp: 1, source: "s", detections: [] })
        );
      });
      rerender({ active: false });
      expect(result.current.frame).toBeNull();
    });

    it("frame_retains_value_on_connection_error", () => {
      // Setup: active=true, simulate message, then simulate error
      const { result } = renderHook(() => useStream(true));
      const frameJson = JSON.stringify({
        jpeg_b64: "kept",
        timestamp: 1,
        source: "s",
        detections: [],
      });
      act(() => {
        instances[0].simulateMessage(frameJson);
      });
      act(() => {
        instances[0].simulateError();
      });
      expect(result.current.frame).toEqual({
        jpeg_b64: "kept",
        timestamp: 1,
        source: "s",
        detections: [],
      });
    });
  });

  describe("Error Propagation", () => {
    it("malformed_json_does_not_update_frame", () => {
      // Setup: Simulate valid message first, then malformed
      const { result } = renderHook(() => useStream(true));
      const validFrame = { jpeg_b64: "v", timestamp: 1, source: "s", detections: [] };
      act(() => {
        instances[0].simulateMessage(JSON.stringify(validFrame));
      });
      // Suppress console.error for the JSON.parse failure
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      act(() => {
        instances[0].simulateMessage("not json");
      });
      consoleSpy.mockRestore();
      expect(result.current.frame).toEqual(validFrame);
    });

    it("error_listener_does_nothing", () => {
      // Expected: No state change, no alert, no error
      const { result } = renderHook(() => useStream(true));
      const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
      act(() => {
        instances[0].simulateError();
      });
      alertSpy.mockRestore();
      expect(result.current.frame).toBeNull();
      expect(alertSpy).not.toHaveBeenCalled();
    });
  });

  describe("Resource Cleanup", () => {
    it("only_one_event_source_exists_at_a_time", () => {
      // Setup: active=true, then false, then true
      // Expected: First instance closed before second created
      const { rerender } = renderHook(
        ({ active }) => useStream(active),
        { initialProps: { active: true } }
      );
      const first = instances[0];
      rerender({ active: false });
      expect(first.close).toHaveBeenCalled();
      rerender({ active: true });
      // Only one unclosed instance exists
      const unclosed = instances.filter(
        (inst) => !inst.close.mock.calls.length
      );
      expect(unclosed.length).toBe(1);
    });
  });
});
