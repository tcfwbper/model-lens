import { expect, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";

expect.extend(matchers);

afterEach(() => {
  cleanup();
});

/**
 * jsdom/cssstyle normalizes "border-style: none" to "" which prevents
 * tests from asserting borderStyle === "none". This patch preserves
 * the "none" value so that inline style assertions work as in a real browser.
 */
(function patchBorderStyleNone() {
  const proto = CSSStyleDeclaration.prototype;
  const desc = Object.getOwnPropertyDescriptor(proto, "borderStyle");
  if (!desc || !desc.set || !desc.get) return;
  const originalGet = desc.get;
  const originalSet = desc.set;
  const store = new WeakMap<CSSStyleDeclaration, string>();
  Object.defineProperty(proto, "borderStyle", {
    get() {
      const override = store.get(this);
      if (override !== undefined) return override;
      return originalGet.call(this);
    },
    set(v: string) {
      if (v === "none") {
        store.set(this, "none");
      } else {
        store.delete(this);
        originalSet.call(this, v);
      }
    },
    enumerable: true,
    configurable: true,
  });
})();
