#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

ui_dir=${1:-src/ui}
pm=${2:-npm}

./dev/ui-clean.sh "$ui_dir"
./dev/ui-install.sh "$ui_dir" "$pm"
