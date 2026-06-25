# Test Specification: `main.test.tsx`

## Source File Under Test
`src/ui/src/main.tsx`

## Test File
`src/ui/src/main.test.tsx`

---

## `main`

### Happy Path — Rendering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `renders_app_inside_strict_mode` | `unit` | Entry point renders App wrapped in React.StrictMode. | Create a DOM element with id `root` and append it to `document.body`. Mock `react-dom/client`'s `createRoot` to return an object with a `render` spy. Mock the `App` component to render a placeholder. | Import `main.tsx` (side-effect execution). | `createRoot` is called with the `#root` DOM element. The `render` spy is called once with a tree containing `<StrictMode><App /></StrictMode>`. |
| `calls_create_root_with_root_element` | `unit` | createRoot receives the DOM element with id "root". | Create a DOM element with id `root` and append it to `document.body`. Mock `react-dom/client`'s `createRoot` to return an object with a `render` spy. | Import `main.tsx` (side-effect execution). | `createRoot` is called exactly once with `document.getElementById("root")` (the element created in setup). |
| `imports_design_tokens_stylesheet` | `unit` | The module imports design-tokens.css as a side-effect. | Mock the CSS import (`design-tokens.css`) to verify it is loaded. Create a DOM element with id `root` and append it to `document.body`. Mock `react-dom/client`'s `createRoot` to return an object with a `render` spy. | Import `main.tsx` (side-effect execution). | The `design-tokens.css` module is imported (mock is resolved/called). |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `does_not_pass_props_to_app` | `unit` | App is rendered with no props. | Create a DOM element with id `root` and append it to `document.body`. Mock `react-dom/client`'s `createRoot` to return an object with a `render` spy. Mock `App` component. | Import `main.tsx` (side-effect execution). | The `App` component is rendered with no props (empty props object or undefined). |
| `create_root_called_only_once` | `unit` | createRoot is invoked exactly once (no duplicate roots). | Create a DOM element with id `root` and append it to `document.body`. Mock `react-dom/client`'s `createRoot` to return an object with a `render` spy. | Import `main.tsx` (side-effect execution). | `createRoot` call count is exactly 1. |

### Edge Cases

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `throws_when_root_element_missing` | `unit` | Runtime error when #root element is absent from DOM. | Do NOT create a `#root` element in the document. Mock `react-dom/client`'s `createRoot`. | Import `main.tsx` (side-effect execution). | A runtime error is thrown (TypeError or similar) because `document.getElementById("root")` returns `null` and the non-null assertion fails when passed to `createRoot`. |
