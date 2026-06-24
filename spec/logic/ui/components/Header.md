# Header

## Overview

Static presentational component that renders the application title bar at the top of the page. Has no interactive behavior, no state, and no props.

## Boundaries

- Owns: rendering the "ModelLens" title with appropriate styling.
- Must not: contain any state or side effects.
- Must not: accept props or callbacks.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| Design Tokens | Visual constants | Consume via CSS custom properties | Must not hardcode values that differ from token definitions |

## Behavior

1. Renders a `<header>` element with:
   - backgroundColor: `var(--color-bg-surface)` (`#FFFFFF`).
   - borderBottom: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - padding: `var(--spacing-md) var(--spacing-xl)` (`12px 24px`).
2. Contains an `<h1>` element with:
   - Text content: "ModelLens".
   - margin: `0`.
   - color: `var(--color-text-primary)` (`#2C3E50`).
   - fontSize: `var(--font-size-heading)` (`1.5rem`).
   - fontWeight: `bold`.

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

- [Design Tokens](../styles/design-tokens.md): defines all visual constants.
- [App](../App.md): parent component that renders Header.
