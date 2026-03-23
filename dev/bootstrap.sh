#!/bin/bash
set -e
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"/../

# Remove caches
./dev/rm-caches.sh

uv pip install -e . --group dev
uv lock
