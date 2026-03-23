# ADR 0001: Initial Python Toolchain Selection

**Date:** 2026-03-23
**Status:** Accepted

## Context
A new Python project requires decisions on package management, code formatting, linting, type checking, and testing tooling. These choices affect developer workflow and CI consistency throughout the project lifetime.

## Decision
The following toolchain is adopted:

| Role | Tool |
|---|---|
| Package / dependency manager | `uv` |
| Code formatter | `black` + `isort` + `docformatter` |
| Linter | `ruff`, `flake8`, `pylint` |
| Type checker | `mypy` (strict mode) |
| Test runner | `pytest` + `pytest-cov` |

Line length is standardised at **120 characters** across all tools.

## Rationale
- **uv** offers significantly faster dependency resolution and installation than pip/pip-tools while remaining compatible with the standard `pyproject.toml` format.
- **black** is opinionated and non-configurable in style, eliminating formatting debates. **isort** and **docformatter** cover import ordering and docstring formatting respectively.
- **ruff** catches most issues quickly; **flake8** and **pylint** are retained for rules not yet covered by ruff.
- **mypy** in strict mode enforces complete type annotation, catching a class of bugs before runtime.
- **pytest** is the de-facto standard for Python testing; `pytest-cov` integrates coverage reporting.

## Alternatives Considered
- **Poetry** for package management — rejected in favour of uv for speed and simplicity.
- **autopep8 / yapf** for formatting — rejected in favour of black's zero-configuration approach.
- **pyright** for type checking — not selected; mypy is more mature in strict-mode usage at the time of this decision.

## Consequences
- All contributors must have `uv` installed; see `dev/uv-install.sh`.
- CI must run the full format-and-test pipeline (`dev/format-and-test.sh`) before merging.
- mypy strict mode means all new code must be fully type-annotated.

## Superseded By / Supersedes
N/A
