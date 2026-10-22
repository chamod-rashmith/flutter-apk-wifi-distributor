#!/usr/bin/env bash
# Shell launcher for Flutter APK Wi-Fi Distributor
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH}"

python3 -m flutter_apk_wifi_distributor.cli "$@"
