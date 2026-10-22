#!/usr/bin/env bash
# Universal one-click installer for flutter-apk-wifi-distributor on macOS / Linux
set -e

echo -e "\n\033[1;36m🚀 Installing flutter-apk-wifi-distributor CLI and Antigravity Plugin...\033[0m"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1. Install CLI tool via pip
echo -e "\033[1;33m📦 Installing Python CLI package (pip install -e)...\033[0m"
python3 -m pip install -e "${PROJECT_ROOT}"

# 2. Deploy Antigravity Plugin to ~/.gemini/config/plugins/flutter-apk-wifi-distributor
GEMINI_PLUGIN_DIR="${HOME}/.gemini/config/plugins/flutter-apk-wifi-distributor"
echo -e "\033[1;33m🤖 Installing Antigravity AI Plugin to: ${GEMINI_PLUGIN_DIR}\033[0m"

mkdir -p "${GEMINI_PLUGIN_DIR}"
cp -R "${PROJECT_ROOT}/plugin/"* "${GEMINI_PLUGIN_DIR}/"
chmod +x "${GEMINI_PLUGIN_DIR}/scripts/"*.sh "${GEMINI_PLUGIN_DIR}/scripts/"*.py 2>/dev/null || true

echo -e "\n\033[1;32m✅ Installation Complete!\033[0m"
echo -e "   👉 CLI Command: 'apk-distribute' is now available system-wide."
echo -e "   👉 AI Plugin  : Successfully registered for Antigravity AI agents."
echo -e "   👉 Try asking : 'Start Wi-Fi distribution server to choose and build Flutter APK'\n"
