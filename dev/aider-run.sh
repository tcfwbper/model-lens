#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

if [[ -z $OPENROUTER_API_KEY ]]; then
    read -sp "OpenRouter API Key: " OPENROUTER_API_KEY
    export OPENROUTER_API_KEY
fi

MODEL="openrouter/anthropic/claude-sonnet-4.6"
AIDER_MODE=

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --mode)
            AIDER_MODE="$2";
            if [[ ! "$AIDER_MODE" =~ ^(spec-logic|spec-test|code-test|code-impl)$ ]]; then
                echo ""
                echo "Invalid mode: $AIDER_MODE"
                echo "Valid modes are: spec-logic, spec-test, code-test, code-impl"
                exit 1
            fi
            shift ;;
        *)
            echo ""
            echo "Unknown parameter: $1"
            exit 1 ;;
    esac
    shift
done

AIDER_ARGS=(--read .aider.instructions.md)

case "$AIDER_MODE" in
    "spec-logic")
        AIDER_ARGS+=(
            --read spec/conventions.md
            --read spec/glossary.md
            --read spec/architecture.md
        )
        ;;
    "spec-test")
        AIDER_ARGS+=(
            --read spec/conventions.md
            --read spec/glossary.md
            --read spec/errors.md
        )
        ;;
    "code-test")
        AIDER_ARGS+=(
            --read spec/conventions.md
            --read spec/glossary.md
            --read spec/errors.md
        )
        ;;
    "code-impl")
        AIDER_ARGS+=(
            --read spec/conventions.md
            --read spec/glossary.md
            --read spec/errors.md
        )
        ;;
esac

aider --model "$MODEL" "${AIDER_ARGS[@]}"
