#!/usr/bin/env bash
set -euo pipefail
exec python3 scripts/sync_runtime_assets.py "$@"
