#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

RUN_ALL=false

for arg in "$@"; do
    case "$arg" in
        --all)
            RUN_ALL=true
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: $0 [--all]" >&2
            exit 1
            ;;
    esac
done

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
if [[ "$RUN_ALL" == true ]]; then
    python -m pytest --cov=src/model_lens --disable-warnings
else
    python -m pytest --cov=src/model_lens --disable-warnings -m "unit"
fi
echo "- pytest: done"

echo "- All Python checks passed"
