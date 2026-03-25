# ADR 0022: Custom exception hierarchy with single string message

**Date:** 2026-03-25
**Status:** Accepted

## Context
When designing error handling in ModelLens, we need a consistent way to define, raise, and catch exceptions across the domain layer, ensuring errors are highly actionable and well-categorized.

## Decision
All project-specific exceptions must derive from a single base class `ModelLensError`. Furthermore, all exception constructors (including `ModelLensError` and all subclasses) must accept exactly one positional argument: a human-readable, actionable `message` string. Storing structured fields (like `key`, `value`) on the exception object is prohibited.

## Rationale
- A unified base class (`ModelLensError`) allows catch-all handlers for domain errors at the boundary (e.g., before returning HTTP responses), safely isolating them from unexpected system errors (`BaseException` or bare `Exception`).
- Enforcing a strict single-string `message` contract forces developers to write complete, actionable error messages at the site where the error is raised, rather than relying on upper layers to format structured data.
- It keeps the exception classes exceptionally simple and free of boilerplate.

## Alternatives Considered
- **Option A:** Use structured exception classes (e.g., `ValidationError(field, value, constraint)`) — rejected because it complicates the exception definitions, requires shared knowledge of formatting across layers, and often leads to generic unstructured strings when developers are lazy.
- **Option B:** Reuse built-in exceptions like `ValueError` or Pydantic's `ValidationError` in the domain layer — rejected because it blurs the line between domain errors and library/built-in errors (`spec/errors.md` specifically mandates keeping domain logic and API validations separate).

## Consequences
- Developers must ensure the string message contains all necessary context (value, constraint, key) at the moment it is raised.
- Machine-parsing exception details from domain errors is harder, but since these are primarily for logs or human-readable API error bodies, this is an acceptable tradeoff for simplicity.

## Superseded By / Supersedes
N/A
