# Conventions for ModelLens

## Naming Conventions
| Artefact | Convention | Example |
|---|---|---|
| Python package | `snake_case` | `model_lens` |
| Python module | `snake_case` | `my_module.py` |
| Python class | `PascalCase` | `MyClass` |
| Python function / variable | `snake_case` | `my_function()` |
| Spec files | `snake_case.md` | `spec/logic/model_lens/my_module.md` |
| Test files | `test_<module>.py` | `test/model_lens/test_my_module.py` |

## Coding Style

### Line Length
- Maximum **120 characters** per line (enforced by black, flake8, pylint, ruff, docformatter).

### Formatter — black
- All code is formatted with **black** (`line-length = 120`, `target-version = ["py311", "py312", "py313"]`).
- Do not manually reformat code that is already black-compliant.

### Import Ordering — isort
- Imports are sorted with **isort** using the Vertical Hanging Indent style (`multi_line_output = 3`).
- Multi-line imports must use parentheses and a trailing comma:
  ```python
  from some_package import (
      ModuleA,
      ModuleB,
      ModuleC,
  )
  ```
- `src/model_lens` is treated as first-party (`known_first_party = ["src/model_lens"]`).
- Standard section order: stdlib → third-party → first-party (`src/model_lens`) → local.

### Docstrings — Google style
- All public modules, classes, functions, and methods must have docstrings.
- Use **Google docstring style** (enforced by ruff pydocstyle and docformatter):
  ```python
  def my_function(x: int) -> str:
      """Convert x to a formatted string.

      Args:
          x: The integer to convert.

      Returns:
          A formatted string representation of x.
      """
  ```
- Summary lines and description blocks are both wrapped at 120 characters (docformatter).

### Type Annotations — mypy strict
- **All** functions and methods must have complete type annotations — parameters and return types.
- mypy runs in `strict` mode; no untyped function bodies or `Any` leakage allowed.
- `ignore_missing_imports = true` is set for third-party stubs that are absent.

### Ruff Rules in Force
| Rule set | Meaning | Notable impact |
|---|---|---|
| `D` | pydocstyle | Docstrings required and correctly formatted |
| `E` / `W` | pycodestyle errors / warnings | Standard PEP 8 style (modulo ignored rules below) |
| `F` | pyflakes | No unused imports, undefined names, etc. |
| `B` | flake8-bugbear | Common bug-prone patterns must be avoided |
| `ISC` | implicit string concatenation | Adjacent string literals must be explicit, not accidental |
| `C4` | flake8-comprehensions | Prefer list/dict/set comprehensions over `map`/`filter`/`lambda` |
| `UP` | pyupgrade | Use modern Python 3.11+ syntax (e.g., `X \| Y` union types) |

### Explicitly Ignored Rules
| Rule | Reason ignored |
|---|---|
| `E302` | black controls blank lines between top-level definitions |
| `W503` | line break *before* binary operator is preferred (over after) |
| `E203` | whitespace before `:` in slices is accepted (black compatible) |
| `B024` | abstract base classes without `abstractmethod` are allowed |
| `B027` | empty methods in abstract classes are allowed |

### General Rules (pylint)
- `duplicate-code`, `too-few-public-methods`, and `useless-import-alias` warnings are suppressed.
- All other pylint rules apply at `max-line-length = 120`.

### Python Version
- Minimum supported version is **Python 3.11**.
- Use modern syntax where applicable: `match`/`case`, `X | Y` type unions, `TypeAlias`, etc.
