#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

echo "=== test.sh ==="

echo "- Start Python checks"

echo "- isort: start"
python -m isort --check-only src/model_lens
echo "- isort: done"

echo "- black: start"
python -m black --check src/model_lens
echo "- black: done"

echo "- docformatter: start"
python -m docformatter -c -r src/model_lens
echo "- docformatter:  done"

echo "- ruff: start"
python -m ruff check src/model_lens
echo "- ruff: done"

echo "- mypy: start"
python -m mypy src/model_lens
echo "- mypy: done"

echo "- pylint: start"
python -m pylint src/model_lens
echo "- pylint: done"

echo "- flake8: start"
python -m flake8 src/model_lens
echo "- flake8: done"

echo "- pytest: start"
python -m pytest --cov=src/model_lens --disable-warnings
echo "- pytest: done"

echo "- All Python checks passed"
