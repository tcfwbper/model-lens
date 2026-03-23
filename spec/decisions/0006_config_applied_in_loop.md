# ADR 0006: Config Changes Applied In-Loop

**Date:** 2026-03-23
**Status:** Accepted

## Context
When the user updates `RuntimeConfig` (e.g. changes target labels), the Detection Pipeline needs to pick up the change. The options are: (a) read config on every frame iteration, or (b) signal the pipeline to stop and restart with the new config.

## Decision
The Detection Pipeline reads `RuntimeConfig` from a shared slot at the start of every frame iteration. No stop/restart signal is issued on config change.

## Rationale
Reading config in-loop is simpler: no signalling mechanism, no race conditions around shutdown/startup, and no dropped frames during the transition. The cost of reading a small struct once per frame is negligible.

## Alternatives Considered
- **Stop/restart pipeline on config change** — rejected because it adds a signalling channel, introduces a gap in the stream during restart, and complicates the pipeline lifecycle.

## Consequences
- Config changes take effect within one frame interval (typically <100 ms).
- The pipeline code has no explicit config-change handling logic; it simply reads the current slot on each iteration.
- The shared config slot must be written atomically to avoid torn reads.

## Superseded By / Supersedes
N/A
