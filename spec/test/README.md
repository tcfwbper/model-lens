# Test Spec Style Guide

This document defines the conventions for writing spec files under `spec/test/model_lens/`.

---

## 1. File Naming and Linking

One spec file per test module, mirroring the source layout:

| Artefact | Path |
|---|---|
| Source module | `src/model_lens/<module>.py` |
| Test spec | `spec/test/model_lens/test_<module>.md` |

---

## 2. File Structure

Each spec file must contain the following sections in order:

```
# Test Specification: `test/model_lens/test_<module>.md`

## Source File Under Test
## Test File
## Imports Required
---
## <N>. `<ClassName>`
### <N>.<M> <Subsection Title>
...
---
## Summary Table
```

---

## 3. Subsection Types

Use only these subsection titles (include only those that are applicable):

| Title | Purpose |
|---|---|
| `Happy Path — Construction` | Valid inputs; verify fields are stored correctly |
| `Happy Path — Default Construction` | Zero-argument construction; verify defaults |
| `Happy Path — Explicit Construction` | Named arguments; verify non-default values |
| `Boundary Values — <field>` | Inputs at or just outside valid range boundaries |
| `Validation Failures` | Invalid inputs that must raise an exception |
| `Validation Failures — <field>` | Narrow to a specific field when multiple fields are tested |
| `Immutability` | Field assignment on a frozen instance must raise |
| `Atomic Replacement` | Constructing a new instance does not mutate the original |
| `Type Hierarchy` | `isinstance` checks and abstract base class enforcement |
| `Catch Behaviour` | Exception caught by its parent class |
| `Data Independence (Copy Semantics)` | Mutation of the source array does not affect the stored value |
| `Read-Only Convention` | Mutation is not enforced; verify it does not raise |
| `Not Frozen` | Non-frozen dataclass; field reassignment must not raise |
| `Abstract Base — Cannot Be Instantiated` | Direct instantiation must raise `TypeError` |

---

## 4. Table Columns

Each subsection contains a Markdown table. Use these columns:

**Most subsections (Input is relevant):**

| Test ID | Description | Input | Expected |
|---|---|---|---|

**Type Hierarchy and similar (no meaningful input):**

| Test ID | Description | Expected |
|---|---|---|

- **Test ID** — the exact function name that will be implemented, in backticks.
- **Description** — one short sentence describing the scenario.
- **Input** — the construct or value passed; use inline code.
- **Expected** — the assertion or exception, using inline code.

---

## 5. Test ID Naming

Pattern: `test_<subject>_<scenario>`

- `<subject>` is the snake_case class or construct name.
- `<scenario>` describes the specific condition.

Examples: `test_local_camera_config_default_device_index`, `test_detection_result_confidence_zero`.

Each Test ID in the spec maps to exactly **one** test function. Do not merge rows.

---

## 6. Summary Table

End every spec file with a summary table:

| Entity | Test Count (approx.) | Key Concerns |
|---|---|---|
| `ClassName` | N | comma-separated list of concerns |

---

## 7. Notes and Callouts

Use blockquotes for design rationale or scope notes that should not become test logic:

> **Note:** Thread-safety of the swap mechanism is the responsibility of the Detection Pipeline.
> Concurrency tests belong in `test/model_lens/test_detection_pipeline.py`.
