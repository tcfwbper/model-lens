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

### Happy Path — Styling

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `header_has_surface_background` | `unit` | Header element has white background color from design token. | | Render `<Header />` | `<header>` element has `backgroundColor` of `#FFFFFF` (or `var(--color-bg-surface)`). |
| `header_has_bottom_border` | `unit` | Header element has a bottom border using border token. | | Render `<Header />` | `<header>` element has `borderBottom` of `1px solid #D4DAE0` (or `1px solid var(--color-border)`). |
| `header_has_correct_padding` | `unit` | Header element has padding from spacing tokens. | | Render `<Header />` | `<header>` element has padding matching `12px 24px` (or `var(--spacing-md) var(--spacing-xl)`). |
| `h1_has_correct_style` | `unit` | H1 element applies heading design tokens. | | Render `<Header />` | `<h1>` has `margin: 0`, `color` of `#2C3E50`, `fontSize` of `1.5rem`, `fontWeight` of `bold`. |
