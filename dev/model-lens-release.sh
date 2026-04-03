#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

bash dev/model-lens-build.sh
bash dev/model-lens-publish.sh
