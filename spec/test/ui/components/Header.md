# Test Specification: `Header.test.tsx`

## Source File Under Test
`src/ui/src/components/Header.tsx`

## Test File
`src/ui/src/components/Header.test.tsx`

---

## `Header`

### Happy Path — Rendering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `renders_header_element` | `unit` | Renders a `<header>` HTML element. | | Render `<Header />` | A `<header>` element is present in the document. |
| `displays_model_lens_title` | `unit` | Displays the text "ModelLens" in an h1 element. | | Render `<Header />` | An `<h1>` element containing the text "ModelLens" is present. |
| `renders_identically_on_rerender` | `unit` | Re-rendering produces the same output. | | Render `<Header />` twice. | Both render results produce identical DOM structure. |
