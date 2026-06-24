# Header

## Overview

Static presentational component that renders the application title bar at the top of the page. Has no interactive behavior, no state, and no props.

## Boundaries

- Owns: rendering the "ModelLens" title with appropriate styling.
- Must not: contain any state or side effects.
- Must not: accept props or callbacks.

## Dependencies

None.

## Behavior

1. Renders a `<header>` element with white background and a subtle bottom border (`#D4DAE0`).
2. Contains an `<h1>` displaying the text "ModelLens" in bold, 1.5rem font size, colored `#2C3E50`.
3. Padding: `12px 24px`.

## Inputs

None (no props).

## Outputs

JSX element representing the header bar.

## Invariants

- Always renders identically regardless of application state.
- Must not trigger re-renders of sibling components.

## Edge Cases

None — purely static.

## Related

- [App](../App.md): parent component that renders Header.
