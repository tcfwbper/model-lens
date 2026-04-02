import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});

// Provide a minimal EventSource stub for jsdom (which doesn't include it)
if (!globalThis.EventSource) {
  globalThis.EventSource = class MockEventSource {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;
    readonly CONNECTING = 0;
    readonly OPEN = 1;
    readonly CLOSED = 2;
    readyState = 0;
    url: string;
    onopen: ((ev: Event) => void) | null = null;
    onmessage: ((ev: MessageEvent) => void) | null = null;
    onerror: ((ev: Event) => void) | null = null;
    constructor(url: string) {
      this.url = url;
    }
    close() {
      this.readyState = 2;
    }
    addEventListener() {}
    removeEventListener() {}
    dispatchEvent() { return false; }
  } as unknown as typeof EventSource;
}

// Mock Image so that setting src triggers onload synchronously
// (jsdom doesn't load images, so onload never fires)
const OriginalImage = globalThis.Image;
class MockImage extends OriginalImage {
  set src(value: string) {
    Object.defineProperty(this, 'src', {
      value,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(this, 'complete', { value: true, configurable: true });
    if (this.onload) {
      this.onload(new Event('load'));
    }
  }
  get src() {
    return '';
  }
}
globalThis.Image = MockImage as typeof Image;
