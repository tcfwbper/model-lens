#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

# Python
python -m isort src/model_lens
python -m black -q src/model_lens
python -m docformatter -i -r src/model_lens
python -m ruff check --fix src/model_lens
