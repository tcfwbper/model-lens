# ADR 0004: Bundled Static Assets

**Date:** 2026-03-23
**Status:** Accepted

## Context
The browser UI (HTML/JS/CSS) needs to be delivered to the client. The options are bundling assets inside the Python package or serving them from an external location (CDN, S3, etc.).

## Decision
Frontend assets are committed into the package and served directly by the web server at startup. No external asset storage is used.

## Rationale
Bundling assets makes the tool self-contained: a single `pip install` gives the user a fully working application with no network access required to serve the UI. Simplifies deployment for a local demo tool.

## Alternatives Considered
- **External asset store (S3 / CDN)** — rejected for MVP; introduces network dependency and operational complexity. Deferred as a post-MVP extensibility point.

## Consequences
- The package size grows by the size of the frontend assets.
- Updating the UI requires a new package release.
- Adding an external asset source later only requires an asset-sync step in the server startup hook.

## Superseded By / Supersedes
N/A
