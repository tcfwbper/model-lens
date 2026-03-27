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

echo "Format code and run test scripts"

./dev/format.sh

if [[ "$RUN_ALL" == true ]]; then
    echo "Running all tests"
    bash dev/test.sh --all
else
    echo "Running unit tests"
    bash dev/test.sh
fi
