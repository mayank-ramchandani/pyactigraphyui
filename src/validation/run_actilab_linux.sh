#!/usr/bin/env bash
# Local processing, no network uploads; pass all options through.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m validation.actilab_cli "$@"
