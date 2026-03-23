# ADR 0003: In-Memory Config Only

**Date:** 2026-03-23
**Status:** Accepted

## Context
The server needs to hold runtime configuration (camera source, target labels). The question is whether this state should be persisted to disk or kept only in memory.

## Decision
`RuntimeConfig` lives in a single shared in-memory slot. There is no file or database persistence; settings are lost on restart.

## Rationale
MVP is a demo tool with a single user. Persisting config adds a Config Store component, file I/O, and migration concerns that deliver no meaningful value at this stage. Users can re-select their settings via the UI after a restart in seconds.

## Alternatives Considered
- **File-based persistence (JSON/TOML)** — rejected for MVP; the Config API already provides the appropriate extension point if this is needed later.
- **Database persistence** — out of scope entirely for a local demo tool.

## Consequences
- Server configuration is reset on every restart.
- The Config API is the only interface to update settings; no external config file is read at runtime.
- Adding persistence later only requires inserting a Config Store behind the existing Config API without changing other components.

## Superseded By / Supersedes
N/A
