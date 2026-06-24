#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

echo "Format code and run test scripts"

./dev/format.sh

if [[ "$RUN_ALL" == true ]]; then
    echo "Running all tests"
    bash dev/test.sh
else
    echo "Running unit tests"
    bash dev/test.sh
fi
