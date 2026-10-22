#!/usr/bin/env bash
# Bash convenience wrapper for Flutter APK Wi-Fi Distributor (macOS & Linux)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/distribute_apk.py"

python3 "${PYTHON_SCRIPT}" "$@"
