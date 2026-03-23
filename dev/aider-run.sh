#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

if [[ -z $OPENROUTER_API_KEY ]]; then
    read -sp "OpenRouter API Key: " OPENROUTER_API_KEY
    export OPENROUTER_API_KEY
fi

MODEL="openrouter/anthropic/claude-sonnet-4.6"
ADD_SPEC=false

for arg in "$@"; do
    case "$arg" in
        --spec)
            ADD_SPEC=true
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: $0 [--spec]" >&2
            exit 1
            ;;
    esac
done

AIDER_ARGS=(--read .aider.instructions.md)

if [[ "$ADD_SPEC" == true ]]; then
    AIDER_ARGS+=(
        --read spec/architecture.md
        --read spec/configuration.md
        --read spec/conventions.md
        --read spec/errors.md
        --read spec/glossary.md
    )
fi

aider --model "$MODEL" "${AIDER_ARGS[@]}"
