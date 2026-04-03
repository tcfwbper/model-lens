#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

PYPI_TOKEN=
read -sp "PyPI Token: " PYPI_TOKEN

uv publish --token "$PYPI_TOKEN"
