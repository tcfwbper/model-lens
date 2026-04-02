#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

HOST="0.0.0.0"
PORT="8080"

for arg in "$@"; do
    case "$arg" in
        --host=*)
            HOST="${arg#*=}"
            ;;
        --port=*)
            PORT="${arg#*=}"
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: $0 [--host=HOST] [--port=PORT]" >&2
            exit 1
            ;;
    esac
done

cd src
python -m uvicorn model_lens.app:create_app --factory --host "$HOST" --port "$PORT"
