#!/usr/bin/env sh
set -eu

if [ "${AZURE_USE_MANAGED_IDENTITY:-false}" = "true" ]; then
    az login --identity --only-show-errors >/dev/null
fi

exec python main.py "$@"
