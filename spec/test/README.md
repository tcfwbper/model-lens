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

**Construction**

| Title | Purpose |
|---|---|
| `Happy Path — Construction` | Valid inputs; verify fields are stored correctly |
| `Happy Path — Default Construction` | Zero-argument construction; verify defaults |
| `Happy Path — Explicit Construction` | Named arguments; verify non-default values |

**Method Behaviour**

| Title | Purpose |
|---|---|
| `Happy Path — <method>` | Successful invocation of a named method or operation; verify return value |
| `Idempotency` | Repeated calls produce the same result with no additional side effects |
| `State Transitions` | Object moves through lifecycle states in the expected sequence |
| `Error Propagation` | Exceptions raised by a dependency surface correctly at the call site |
| `Ordering — <criterion>` | Output sequence satisfies a named ordering guarantee |

**Input Validity**

| Title | Purpose |
|---|---|
| `Boundary Values — <field>` | Inputs at or just outside valid range boundaries |
| `None / Empty Input` | `None` or an empty collection supplied in place of a value; verify acceptance or rejection |
| `Validation Failures` | Invalid inputs that must raise an exception |
| `Validation Failures — <field>` | Narrow to a specific field when multiple fields are tested |

**Object Characteristics**

| Title | Purpose |
|---|---|
| `Immutability` | Field assignment on a frozen instance must raise |
| `Not Frozen` | Non-frozen dataclass; field reassignment must not raise |
| `Read-Only Convention` | Mutation is not enforced; verify it does not raise |
| `Atomic Replacement` | Constructing a new instance does not mutate the original |
| `Data Independence (Copy Semantics)` | Mutation of the source array does not affect the stored value |

**Type and Exception**

| Title | Purpose |
|---|---|
| `Type Hierarchy` | `isinstance` checks and abstract base class enforcement |
| `Catch Behaviour` | Exception caught by its parent class |

**Resource and Concurrency**

| Title | Purpose |
|---|---|
| `Resource Cleanup` | `close()`, `__exit__`, or equivalent teardown releases resources and leaves the object inert |
| `Concurrent Behaviour` | Correct behaviour under concurrent or interleaved access; maps to the `race` category in §4 |

---

## 4. Test Categories

Every test row must be assigned exactly one category:

| Category | Meaning |
|---|---|
| `unit` | Exercises a single class or function in isolation; no I/O, no threads |
| `e2e` | Exercises a full pipeline path from configuration to observable output |
| `race` | Asserts correct behaviour under concurrent access or timing conditions |

The category is recorded in the `Category` column of every test table (see §5) and summarised in the Summary Table (see §7).

---

## 5. Table Columns

Each subsection contains a Markdown table. Use these columns:

**Most subsections (Input is relevant):**

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|

**Type Hierarchy and similar (no meaningful input):**

| Test ID | Category | Description | Expected |
|---|---|---|---|

- **Test ID** — the exact function name that will be implemented, in backticks.
- **Category** — one of `unit`, `e2e`, or `race` (see §4).
- **Description** — one short sentence describing the scenario.
- **Input** — the construct or value passed; use inline code.
- **Expected** — the assertion or exception, using inline code.

---

## 6. Test ID Naming

Pattern: `test_<subject>_<scenario>`

- `<subject>` is the snake_case class or construct name.
- `<scenario>` describes the specific condition.

Examples: `test_local_camera_config_default_device_index`, `test_detection_result_confidence_zero`.

Each Test ID in the spec maps to exactly **one** test function. Do not merge rows.

---

## 7. Summary Table

End every spec file with a summary table:

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `ClassName` | N | N | N | N | comma-separated list of concerns |

---

## 8. Notes and Callouts

Use blockquotes for design rationale or scope notes that should not become test logic:

> **Note:** Thread-safety of the swap mechanism is the responsibility of the Detection Pipeline.
> Concurrency tests belong in `test/model_lens/test_detection_pipeline.py`.
