#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

if [[ -z $OPENROUTER_API_KEY ]]; then
    read -sp "OpenRouter API Key: " OPENROUTER_API_KEY
    export OPENROUTER_API_KEY
fi

MODEL="openrouter/anthropic/claude-sonnet-4.6"
ALLOW_SPEC=false
ALLOW_TEST=false

for arg in "$@"; do
    case "$arg" in
        --spec)
            ALLOW_SPEC=true
            ;;
        --test)
            ALLOW_TEST=true
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: $0 [--spec] [--test]" >&2
            exit 1
            ;;
    esac
done

AIDER_ARGS=(--read .aider.instructions.md --read dev)

if [[ "$ALLOW_SPEC" != true ]]; then
    AIDER_ARGS+=(--read spec)
fi

if [[ "$ALLOW_TEST" != true ]]; then
    AIDER_ARGS+=(--read test)
fi

aider --model "$MODEL" "${AIDER_ARGS[@]}"
