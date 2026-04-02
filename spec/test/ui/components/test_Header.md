# Test Specification: `test/ui/components/test_Header.md`

## Source File Under Test

`src/ui/components/Header.tsx`

## Test File

`test/ui/components/Header.test.tsx`

## Imports Required

```tsx
import { render, screen } from "@testing-library/react";
import Header from "../../../src/ui/components/Header";
```

---

## 1. `Header`

### 1.1 Happy Path — Rendering

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_header_renders_app_title` | `unit` | Displays "ModelLens" text | render `<Header />` | text `"ModelLens"` is present in the document |
| `test_header_renders_as_heading` | `unit` | Title is rendered as a heading element | render `<Header />` | `screen.getByRole("heading")` contains `"ModelLens"` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `Header` | 2 | 2 | 0 | 0 | static title rendering |
