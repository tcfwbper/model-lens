# Project Structure for ModelLens

## Core Principle
This document defines the canonical directory layout and naming conventions for ModelLens.

## Directory Responsibilities

### `dev/`
- Shell scripts for local developer workflows only (formatting, venv management, test runners, and so on).
- Must not be imported by production code.

### `spec/`
- **Authority:** All designs, API contracts, Test specs and logic rules live here first.
- `architecture.md` — overall system design, component diagram, data models.
- `configuration.md` — runtime configuration keys, types, defaults, and validation rules.
- `conventions.md` — coding style and naming conventions.
- `errors.md` — exception hierarchy, error handling strategy, and logging conventions.
- `glossary.md` — canonical domain terminology used in code and specs.
- `structure.md` — this file; canonical directory layout.
- `workflow.md` — development workflow defined here.
- `decisions/` — Architecture Decision Records (ADRs); read before proposing design changes.
- `logic/` — one `.md` file per module, describing its behaviour and rules.
- `test/` — one `.md` file per module, listing test cases (input → expected output).
- **Rule:** No code in `src/` may contradict a spec file. If a conflict arises, update the spec first.

### `src/model_lens/`
- Contains only production code.
- Code primarily developed in Python.
- No ad-hoc scripts, debug prints, or one-off utilities.
- Each module must have a corresponding spec in `spec/logic/model_lens`.

### `test/model_lens`
- Mirrors the structure of `src/model_lens/`.
- Test file naming: `test_<module_name>.py`
- Each test file must map to a spec in `spec/test/model_lens`.
