# main

## Overview

Application entry point for the ModelLens UI. Mounts the root React component (`App`) into the DOM under React StrictMode. Does not contain any application logic — its sole purpose is bootstrapping the React render tree and loading global styles.

## Boundaries

- Owns: locating the DOM mount point, creating the React root, and triggering the initial render.
- Owns: importing the global design-tokens stylesheet so it is available to all descendant components.
- Delegates: all application behavior to the `App` component.
- Must not: contain any application state, side effects, or business logic.
- Must not: render any UI directly — delegates entirely to `App`.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `App` component | Root UI tree | Render as the sole child of `StrictMode` | Must not pass props or configure behavior |
| `design-tokens.css` | Global CSS custom properties | Import as a side-effect stylesheet | Must not override token values inline |
| DOM (`#root` element) | Mount target | Query via `document.getElementById("root")` | Must not create or modify DOM elements beyond the React root |

Construction constraint: This is a top-level script module, not a component or hook. It executes once on page load.

## Behavior

1. Imports the global `design-tokens.css` stylesheet (side-effect import).
2. Retrieves the DOM element with id `root` via `document.getElementById("root")`.
3. Creates a React root bound to the retrieved DOM element using `createRoot`.
4. Renders `App` wrapped in `React.StrictMode` into the root.

## Inputs

| Field | Type | Source | Description |
|---|---|---|---|
| `#root` DOM element | HTMLElement | `index.html` | The mount point provided by the HTML shell |

## Outputs

Mounts the React application tree into the DOM. No return value (module side-effect).

## Invariants

- Must wrap `App` in `StrictMode` — never render `App` without it.
- Must import design tokens before rendering so CSS custom properties are available to all components.
- Must not render more than one root or call `createRoot` more than once.
- Assumes the `#root` element exists in the document (non-null assertion).

## Edge Cases

- Condition: `#root` element is missing from the HTML document.
  Expected: Runtime error (non-null assertion failure). This is not handled gracefully — the HTML shell is expected to always provide the element.

## Related

- [App](./App.md): root component rendered by this entry point.
- [Design Tokens](./styles/design-tokens.md): global CSS custom properties loaded here.
