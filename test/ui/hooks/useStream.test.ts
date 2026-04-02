import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useStream } from "../../../src/ui/src/hooks/useStream";

type EventSourceListener = (event: MessageEvent | Event) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  listeners: Record<string, EventSourceListener[]> = {};
  closeSpy = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventSourceListener) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: EventSourceListener) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter((l) => l !== listener);
    }
  }

  close() {
    this.closeSpy();
  }

  dispatchMessage(data: string) {
    const event = new MessageEvent("message", { data });
    this.listeners["message"]?.forEach((l) => l(event));
  }

  dispatchError() {
    const event = new Event("error");
    this.listeners["error"]?.forEach((l) => l(event));
  }
}

describe("useStream", () => {
  let alertSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
    alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function latestInstance(): MockEventSource {
    return MockEventSource.instances[MockEventSource.instances.length - 1];
  }

  // 1.1 Happy Path — Connection Lifecycle

  it("test_use_stream_opens_event_source_when_active", () => {
    renderHook(() => useStream(true));
    expect(MockEventSource.instances.length).toBe(1);
    expect(latestInstance().url).toBe("/stream");
  });

  it("test_use_stream_does_not_open_when_inactive", () => {
    renderHook(() => useStream(false));
    expect(MockEventSource.instances.length).toBe(0);
  });

  it("test_use_stream_closes_on_deactivate", () => {
    const { rerender } = renderHook(({ active }) => useStream(active), {
      initialProps: { active: true },
    });

    const instance = latestInstance();
    rerender({ active: false });

    expect(instance.closeSpy).toHaveBeenCalled();
  });

  it("test_use_stream_closes_on_unmount", () => {
    const { unmount } = renderHook(() => useStream(true));
    const instance = latestInstance();

    unmount();

    expect(instance.closeSpy).toHaveBeenCalled();
  });

  it("test_use_stream_reopens_on_reactivate", () => {
    const { rerender } = renderHook(({ active }) => useStream(active), {
      initialProps: { active: true },
    });

    rerender({ active: false });
    rerender({ active: true });

    expect(MockEventSource.instances.length).toBe(2);
  });

  // 1.2 Happy Path — Frame Processing

  it("test_use_stream_parses_frame_from_message", () => {
    const { result } = renderHook(() => useStream(true));
    const instance = latestInstance();

    const frameData = {
      jpeg_b64: "abc",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };

    act(() => {
      instance.dispatchMessage(JSON.stringify(frameData));
    });

    expect(result.current.frame).toEqual(frameData);
  });

  it("test_use_stream_replaces_frame_on_new_message", () => {
    const { result } = renderHook(() => useStream(true));
    const instance = latestInstance();

    const frame1 = {
      jpeg_b64: "frame1",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };
    const frame2 = {
      jpeg_b64: "frame2",
      timestamp: 2.0,
      source: "local:0",
      detections: [],
    };

    act(() => instance.dispatchMessage(JSON.stringify(frame1)));
    act(() => instance.dispatchMessage(JSON.stringify(frame2)));

    expect(result.current.frame).toEqual(frame2);
  });

  it("test_use_stream_frame_null_when_inactive", () => {
    const { result } = renderHook(() => useStream(false));
    expect(result.current.frame).toBeNull();
  });

  it("test_use_stream_frame_reset_on_deactivate", () => {
    const { result, rerender } = renderHook(({ active }) => useStream(active), {
      initialProps: { active: true },
    });

    const instance = latestInstance();
    const frameData = {
      jpeg_b64: "abc",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };

    act(() => instance.dispatchMessage(JSON.stringify(frameData)));
    expect(result.current.frame).toEqual(frameData);

    rerender({ active: false });
    expect(result.current.frame).toBeNull();
  });

  // 1.3 Happy Path — Detection Data

  it("test_use_stream_parses_detections", () => {
    const { result } = renderHook(() => useStream(true));
    const instance = latestInstance();

    const frameData = {
      jpeg_b64: "abc",
      timestamp: 1.0,
      source: "local:0",
      detections: [
        {
          label: "cat",
          confidence: 0.87,
          bounding_box: [0.1, 0.2, 0.4, 0.6],
          is_target: true,
        },
      ],
    };

    act(() => instance.dispatchMessage(JSON.stringify(frameData)));

    expect(result.current.frame!.detections[0]).toEqual({
      label: "cat",
      confidence: 0.87,
      bounding_box: [0.1, 0.2, 0.4, 0.6],
      is_target: true,
    });
  });

  it("test_use_stream_empty_detections", () => {
    const { result } = renderHook(() => useStream(true));
    const instance = latestInstance();

    const frameData = {
      jpeg_b64: "abc",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };

    act(() => instance.dispatchMessage(JSON.stringify(frameData)));

    expect(result.current.frame!.detections).toEqual([]);
  });

  // 1.4 Error Propagation

  it("test_use_stream_error_does_not_alert", () => {
    renderHook(() => useStream(true));
    const instance = latestInstance();

    act(() => instance.dispatchError());

    expect(alertSpy).not.toHaveBeenCalled();
  });

  it("test_use_stream_error_does_not_clear_frame", () => {
    const { result } = renderHook(() => useStream(true));
    const instance = latestInstance();

    const frameData = {
      jpeg_b64: "abc",
      timestamp: 1.0,
      source: "local:0",
      detections: [],
    };

    act(() => instance.dispatchMessage(JSON.stringify(frameData)));
    act(() => instance.dispatchError());

    expect(result.current.frame).toEqual(frameData);
  });

  // 1.5 Resource Cleanup

  it("test_use_stream_close_called_once_on_deactivate", () => {
    const { rerender } = renderHook(({ active }) => useStream(active), {
      initialProps: { active: true },
    });

    const instance = latestInstance();
    rerender({ active: false });

    expect(instance.closeSpy).toHaveBeenCalledTimes(1);
  });

  it("test_use_stream_no_close_if_never_activated", () => {
    const { unmount } = renderHook(() => useStream(false));

    unmount();

    // No EventSource was created, so no close should be called
    expect(MockEventSource.instances.length).toBe(0);
  });
});
