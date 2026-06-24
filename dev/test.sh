#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

echo "=== test.sh ==="

echo "- Start Python checks"

echo "- ruff: start"
python -m ruff check src/model_lens
echo "- ruff: done"

echo "- mypy: start"
python -m mypy src/model_lens
echo "- mypy: done"

echo "- pytest: start"
python -m pytest --cov=src/model_lens --cov-report=term-missing --disable-warnings
echo "- pytest: done"

echo "- All Python checks passed"
