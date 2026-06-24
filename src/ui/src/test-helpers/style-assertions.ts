/**
 * Shared style assertion helpers for design-token-based UI tests.
 * Provides utilities to inspect inline styles on rendered elements
 * and to parse CSS custom property declarations from raw CSS text.
 */

/**
 * Parses CSS custom property declarations from a :root block in raw CSS text.
 * Returns a map of property name -> value (trimmed, without trailing semicolons).
 */
export function parseRootTokens(cssText: string): Map<string, string> {
  const tokens = new Map<string, string>();
  // Find :root { ... } block
  const rootMatch = cssText.match(/:root\s*\{([^}]*)\}/s);
  if (!rootMatch) return tokens;

  const declarations = rootMatch[1];
  // Match each custom property declaration
  const propRegex = /(--[\w-]+)\s*:\s*([^;]+)/g;
  let match: RegExpExecArray | null;
  while ((match = propRegex.exec(declarations)) !== null) {
    tokens.set(match[1].trim(), match[2].trim());
  }
  return tokens;
}

/**
 * Asserts that an element's inline style contains the given property-value pairs.
 * Accepts both the resolved value and the CSS variable form as valid matches.
 */
export function expectInlineStyle(
  element: HTMLElement,
  styles: Record<string, string | string[]>,
): { pass: boolean; failures: string[] } {
  const failures: string[] = [];
  const inlineStyle = element.style;

  for (const [prop, expected] of Object.entries(styles)) {
    const actual =
      inlineStyle.getPropertyValue(prop) ||
      (inlineStyle as unknown as Record<string, string>)[prop];
    const acceptedValues = Array.isArray(expected) ? expected : [expected];
    if (!acceptedValues.some((v) => actual === v)) {
      failures.push(
        `Expected ${prop} to be one of [${acceptedValues.join(", ")}], got "${actual}"`,
      );
    }
  }

  return { pass: failures.length === 0, failures };
}
