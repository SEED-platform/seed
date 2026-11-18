#!/bin/bash

set -e

cd "$(dirname "$0")/.."

WORKERS="${HYPERCORN_WORKERS:-$(nproc)}"
WORKERS=$(($WORKERS > 1 ? $WORKERS : 1))

exec uv run hypercorn config.asgi:seed --bind 127.0.0.1:8000 --workers "$WORKERS"
