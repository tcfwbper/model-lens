# ADR 0021: Standard library tomllib for configuration parsing

**Date:** 2026-03-25
**Status:** Accepted

## Context
ModelLens uses TOML for its optional configuration file. We needed to choose a library to parse this file. Various third-party libraries exist (like `toml`, `tomlkit`, `rtoml`), but Python 3.11 introduced `tomllib` into the standard library.

## Decision
We will strictly use Python 3.11+ standard library `tomllib` for parsing the TOML configuration file, explicitly prohibiting the use of third-party TOML libraries.

## Rationale
- Using the standard library avoids adding an external runtime dependency, keeping the distribution smaller and more secure.
- `tomllib` fully supports TOML v1.0.0.
- For our use case (reading configuration once at startup), `tomllib` provides sufficient functionality (parsing to a Python dictionary) without needing formatting preservation or write capabilities (which `tomllib` lacks, but we don't need).

## Alternatives Considered
- **Option A:** Use `toml` package — rejected because it is mostly unmaintained and not fully TOML 1.0 compliant.
- **Option B:** Use `tomlkit` — rejected because its main feature is style-preserving read/write, which adds unnecessary complexity and overhead for our read-only needs.

## Consequences
- We cannot programmatically write or modify the TOML config file using `tomllib` (it is read-only). This is acceptable as configuration is meant to be authored by the user or supplied via environment variables.
- We must maintain Python 3.11+ as our minimum runtime requirement, which aligns with modern Python ecosystem standards.

## Superseded By / Supersedes
N/A
