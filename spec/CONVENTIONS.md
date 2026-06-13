# Conventions

## Language & Toolchain

### Backend (Python)
- Language: Python 3.11+
- Linter / Formatter: `ruff` (covers style, import ordering, docstrings, and formatting)
- Type Checker: `mypy` (strict mode)
- Test Runner: `pytest` with `pytest-cov` and `pytest-mock`

### Frontend (TypeScript / React)
- Language: TypeScript (strict)
- UI Framework: React
- Build Tool: Vite
- Test Runner: Vitest
- Linter: ESLint

## Naming

| Kind | Style | Example |
|---|---|---|
| Python package | `snake_case` | `model_lens` |
| Python module | `snake_case` | `my_module.py` |
| Python class | `PascalCase` | `MyClass` |
| Python function / variable | `snake_case` | `my_function()` |
| Python test file | `test_<module>.py` | `test_my_module.py` |
| TS/React component file | `PascalCase.tsx` | `StreamViewer.tsx` |
| TS/React hook file | `use<Name>.ts` | `useConfig.ts` |
| TS type / interface | `PascalCase` | `CameraConfig` |
| TS function / variable | `camelCase` | `handleChange()` |
| TS constant | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Spec files | `UPPER_SNAKE_CASE.md` | `ARCHITECTURE.md` |
| Config env var | `ML_<SECTION>_<KEY>` | `ML_SERVER_PORT` |

## Code Location

### Backend
- `src/model_lens/` — production Python code only; no ad-hoc scripts or debug utilities.
- `tests/model_lens/` — one `test_<module_name>.py` per production module. Additional test helpers (e.g. `conftest.py`) are permitted without a corresponding spec.

### Frontend
- `src/ui/src/components/` — React UI components.
- `src/ui/src/hooks/` — custom React hooks.
- `src/ui/src/` — top-level app entry and global styles.

### Dev Scripts
- `dev/` — shell scripts for local developer workflows (formatting, venv management, test runners). Must not be imported by production code.

### Spec
- `spec/` — all designs, API contracts, and conventions live here first. No code in `src/` may contradict a spec file; update the spec first if there is a conflict.

## Error Handling

### Core Principle
Errors must be **explicit, typed, and traceable**. Never swallow exceptions silently. All public functions communicate failure through typed exceptions — never via sentinel values (e.g. `None`, `-1`, or `""` to signal error).

### Exception Hierarchy
All project-specific exceptions derive from `ModelLensError`, defined in `src/model_lens/exceptions.py`. Never raise bare `Exception` or `BaseException` in production code.

### Boundary Rule
At system boundaries (entry points, external library calls), catch third-party exceptions and re-raise as the appropriate `ModelLensError` subclass:

```python
try:
    result = some_external_lib.call()
except SomeExternalError as exc:
    raise OperationError("Description of what failed") from exc
```

### When to Raise vs. Return

| Situation | Approach |
|---|---|
| Invalid input from caller | Raise `ValidationError` |
| External system unavailable | Raise `HardwareError` or `OperationError` |
| True optional result | Return `T \| None` with clear docstring |
| Expected empty collection | Return `[]` / `{}` — not an error |
| Unrecoverable internal state | Raise `ModelLensError` with full context message |

Never use exceptions for flow control.

### Exception Message Format
Messages must be actionable — include what happened, what value caused it, and where applicable:

```python
raise ValidationError(f"Temperature threshold must be positive, got {value!r}")
```

### Logging
Use the standard `logging` module. Never use `print()` in production code. Obtain the logger at module level:

```python
logger = logging.getLogger(__name__)
```

| Level | When to use |
|---|---|
| `DEBUG` | Detailed internal state, loop iterations, intermediate values |
| `INFO` | Normal milestones: module initialised, task completed |
| `WARNING` | Recoverable unexpected state; operation continues |
| `ERROR` | Operation failed; exception will be raised or was caught at boundary |
| `CRITICAL` | System-level failure; process may not continue |

Log before raising at boundaries so the error appears in logs even if the caller does not re-log it.

### HTTP API Error Conventions
All error responses use the shape `{ "detail": "<human-readable message>" }`.

| Status Code | Condition |
|---|---|
| `202 Accepted` | Resource not yet available (e.g. no frames yet) |
| `400 Bad Request` | Malformed request body |
| `422 Unprocessable Entity` | Data validation fails |
| `500 Internal Server Error` | Unexpected server failure |

Pydantic `ValidationError` (API layer) and `model_lens.exceptions.ValidationError` (domain layer) must never be confused or cross-imported. Fatal startup errors (`ConfigurationError`, `OperationError`, `ParseError`, `RuntimeError` from `DetectionPipeline`) are logged at `CRITICAL` level and result in `sys.exit(1)`.

## Testing

### Backend
- Framework: `pytest`
- Each production module in `src/model_lens/` must have a corresponding `test_<module_name>.py` in `tests/model_lens/`.
- Mocking: `pytest-mock` (`mocker` fixture).
- Coverage: `pytest-cov`.

### Frontend
- Framework: Vitest
- Test files named `*.test.ts` / `*.test.tsx`.
- Use React Testing Library patterns for component tests.

## Imports

Imports are sorted and grouped by `ruff` (isort-compatible rules):

1. Standard library
2. Third-party packages
3. First-party (`src/model_lens`)
4. Local / relative

Multi-line imports must use parentheses and a trailing comma:

```python
from some_package import (
    ModuleA,
    ModuleB,
    ModuleC,
)
```

## Code Style

### File Header (Python)
Every new `.py` file under `src/model_lens/` must begin with the Apache 2.0 copyright notice before any imports or the module docstring:

```python
# Copyright <YEAR> ModelLens Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

Replace `<YEAR>` with the current year. The copyright owner is always `ModelLens Contributors`.

### Line Length
Maximum **120 characters** per line (enforced by `ruff`).

### Docstrings
All public modules, classes, functions, and methods must have Google-style docstrings:

```python
def my_function(x: int) -> str:
    """Convert x to a formatted string.

    Args:
        x: The integer to convert.

    Returns:
        A formatted string representation of x.

    Raises:
        ValidationError: If x is negative.
    """
```

### Type Annotations
All functions and methods must have complete type annotations (parameters and return types). `mypy` runs in `strict` mode; no untyped function bodies or implicit `Any` allowed.

### Ruff Rules

| Rule set | Meaning |
|---|---|
| `D` | pydocstyle — docstrings required and correctly formatted |
| `E` / `W` | pycodestyle errors / warnings |
| `F` | pyflakes — no unused imports, undefined names |
| `B` | flake8-bugbear — avoid bug-prone patterns |
| `ISC` | implicit string concatenation check |
| `C4` | prefer comprehensions over `map`/`filter`/`lambda` |
| `UP` | pyupgrade — use modern Python 3.11+ syntax |

Ignored rules: `B024`, `B027` (abstract base class flexibility).

### Python Version
Minimum Python 3.11. Use modern syntax where applicable: `match`/`case`, `X | Y` union types, `TypeAlias`, etc.

### TypeScript / React Style
- Use functional components with hooks; no class components.
- Prefer explicit return types on exported functions and hooks.
- Use `const` by default; `let` only when reassignment is necessary.
- Avoid global style pollution; scope styles to components.
