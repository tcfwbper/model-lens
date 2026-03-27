# Development Workflow for ModelLens

## Core Principle
All development follows **SDD (Specification-Driven Development) + TDD (Test-Driven Development)**.

Design specifications are the source of truth. Implementation must always align with the specs in `spec/`.

---

## Workflow Phases

### Phase 1: Design & Specification (SDD)
**Status:** Design-First is mandatory.

1. **Identify the requirement** — What feature or bug fix is needed?

2. **Check existing specs** — Before implementing:
   - Look for relevant `.md` files in `spec/logic` (module behavior)
   - Check `spec/test/` (test specifications)
   - Check `spec/architecture.md` (system-wide constraints)
   - Check `spec/configuration.md` (runtime configuration needs)
   - Check `spec/errors.md` (exception hierarchy and error handling)
   - Check `spec/glossary.md` (canonical domain terminology)

3. **If spec exists & is sufficient:**
   - Proceed to Phase 2: Test
   - Implementation must strictly follow the spec

4. **If spec is missing or incomplete:**
   - **DO NOT code yet**
   - Create a new spec file in `spec/logic/model_lens/<module_name>.md` describing:
     - Purpose and responsibilities
     - Function signatures (inputs, outputs)
     - Behavior rules and edge cases
     - Any invariants or constraints
     - Examples of expected behavior
   - Get spec approval before moving forward

5. **If spec contradicts the request:**
   - Alert the user before proceeding
   - Update spec first, then implement

---

### Phase 2: Test Specification (TDD)
**Status:** Tests must be written before implementation.

1. **Create a test spec** in `spec/test/<module_name>.md`:
   - List all test cases as: **Input → Expected Output**
   - Include edge cases and error conditions
   - Ensure coverage of all behavior described in `spec/logic/model_lens/<module_name>.md`

2. **Write test code** in `test/model_lens/test_<module_name>.py`:
   - Test file path must mirror `src/model_lens/<module_name>.py`
   - Follow naming: `test_<function_name>` for each function
   - Use assertions to validate expected behavior
   - All tests must reference test cases in `spec/test/<module_name>.md`

3. **Run unit tests to verify they fail:**
   ```bash
   dev/test.sh
   ```
   - Runs only tests marked `unit` by default
   - All new unit tests should initially FAIL (red) — this is expected

---

### Phase 3: Implementation (Minimal Code)
**Status:** Code only what is needed to pass tests.

1. **Write minimal code** in `src/model_lens/<module_name>.py`:
   - Implement only what is required to pass tests
   - Follow all conventions from `spec/conventions.md`:
     - **Naming:** `snake_case` functions, `PascalCase` classes
     - **Line length:** Max 120 characters
     - **Formatter:** All code must be black-compliant
     - **Imports:** Sorted with isort
     - **Docstrings:** Google style for all public APIs

2. **Ensure code quality:**
   - No debug prints, ad-hoc code, or one-off utilities
   - Every module must have a docstring
   - Every function/method must be typed and documented

3. **Run unit tests:**
   ```bash
   dev/test.sh
   ```
   - All unit tests must PASS (green)
   - No unit test failures or errors allowed before commit
   - E2E and race tests are run in CI only (`dev/test.sh --all`)

---

## Quality Gates

Before committing any code:

1. **Code Formatting:**
   ```bash
   dev/format.sh
   ```
   - Runs black, isort, and docformatter
   - Fix any violations before committing

2. **Unit Tests Pass:**
   ```bash
   dev/test.sh
   ```
   - Zero unit test failures
   - 100% of new functionality must have unit test coverage
   - E2E and race tests are not required locally; they run in CI via `dev/test.sh --all`

3. **Spec is Updated:**
   - All specs in `spec/` match the implementation
   - No contradictions between code and documentation

---

## Workflow Checklist

- [ ] **Design:** Is there a spec for this feature/fix?
  - [ ] If no: Create `spec/logic/model_lens/<module_name>.md` first
  - [ ] If yes: Does the spec match the request? Update if needed.
- [ ] **Tests:** Is there a `spec/test/model_lens/<module_name>.md`?
  - [ ] If no: Create test spec with input → output cases
  - [ ] Write `test/model_lens/test_<module_name>.py` before implementation
  - [ ] Run `dev/test.sh` — unit tests should initially FAIL
- [ ] **Code:** Implement minimal functionality
  - [ ] Add code to `src/model_lens/<module_name>.py`
  - [ ] Follow `spec/conventions.md` strictly
  - [ ] Add docstrings (Google style, 120 char max)
  - [ ] Run `dev/format.sh` — ensure black/isort/docformatter pass
  - [ ] Run `dev/test.sh` — all unit tests must PASS
- [ ] **Review:** Are all quality gates met?
  - [ ] Code is formatted correctly
  - [ ] All unit tests pass (E2E and race tests verified in CI)
  - [ ] Specs are up-to-date and consistent
  - [ ] No ad-hoc or debug code remains

---

## Commands Reference

| Command | Purpose |
|---------|---------|
| `dev/test.sh` | Run unit tests only (default); verify they pass before commit |
| `dev/test.sh --all` | Run full test suite including E2E and race tests (CI only) |
| `dev/format.sh` | Format code (black, isort, docformatter) |
| `dev/format-and-test.sh` | Format then run unit tests |
| `dev/format-and-test.sh --all` | Format then run full test suite including E2E and race tests (CI only) |
| `dev/venv-create.sh` | Create Python virtual environment |
| `dev/venv-reset.sh` | Reset virtual environment to clean state |
| `dev/bootstrap.sh` | Full project setup (venv + install deps) |

---

## Key Principles

1. **Specs are Law** — Code must never contradict a spec; update spec first.
2. **Tests First** — Write tests before code; red → green → refactor.
3. **Minimal Implementation** — Add only the code needed to pass tests.
4. **Code Quality** — Enforce formatting, naming, and docstring rules consistently.
5. **Traceability** — Every test references a spec; every module has a design document.
