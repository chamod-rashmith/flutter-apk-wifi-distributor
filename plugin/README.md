# Flutter APK Wi-Fi Distributor & RAM Optimizer Plugin

An Antigravity plugin for Flutter developers that solves two major workflow pain points:
1. **Cable-free APK Testing & On-Demand Building:** Launch an embedded local Wi-Fi server, choose whatever package you need (Split APKs, Universal Release, or Debug), trigger the build with real-time logs, and download directly to your mobile phone with 1 tap.
2. **Windows RAM Optimization:** Automatically terminates memory-hogging Gradle daemons (`.\gradlew --stop`) and flushes process working sets immediately after build completion and upon server shutdown (reclaiming 4 GB – 8 GB+ RAM).

## 🚀 One-Line Installation

To install both the global `apk-distribute` CLI and register this plugin into Antigravity:

### Windows (PowerShell)
```powershell
git clone https://github.com/chamod-rashmith/flutter-apk-wifi-distributor.git; cd flutter-apk-wifi-distributor; powershell -ExecutionPolicy Bypass -File .\bin\install.ps1
```

### Windows (CMD)
```cmd
git clone https://github.com/chamod-rashmith/flutter-apk-wifi-distributor.git && cd flutter-apk-wifi-distributor && powershell -ExecutionPolicy Bypass -File .\bin\install.ps1
```

### macOS / Linux (Bash)
```bash
git clone https://github.com/chamod-rashmith/flutter-apk-wifi-distributor.git && cd flutter-apk-wifi-distributor && chmod +x ./bin/install.sh && ./bin/install.sh
```

---

## Key Features

- 🌐 **Launch Server First:** Start the distribution server immediately without building beforehand.
- ⚡ **In-Portal Package Selection:** Choose from Split APKs (arm64, arm32, x86_64), Universal Release APK, or Debug APK directly from your phone browser or CLI prompt.
- 🔨 **1-Tap Background Compilation:** Triggers Flutter compilation with live log streaming.
- 🧹 **Zero RAM Leaks:** Terminates lingering Gradle daemons (`.\gradlew --stop`), flushes Windows working sets, and runs garbage collection.
- 📶 **Auto-detected Local Wi-Fi:** Detects the machine's local IPv4 address and hosts a responsive dark-mode portal on port 8080 (with automatic port conflict fallback).
- 📱 **Multi-Package Download Cards:** Shows all available APKs with architecture tags, file sizes, timestamps, and direct download links.

---

## Usage

### In Antigravity Chat
Simply ask:
- *"Launch Wi-Fi server to choose and build my Flutter APK"*
- *"Build split APKs and share to my phone over Wi-Fi"*
- *"Clean Gradle RAM and distribute the APK to my mobile"*

### From PowerShell / Terminal
Navigate to any Flutter project directory and run:

```powershell
# 1. Launch server first (interactive selection from phone browser):
apk-distribute --server
# (Or using python script directly):
python "$HOME\.gemini\config\plugins\flutter-apk-wifi-distributor\scripts\distribute_apk.py" --server

# 2. Or interactive terminal menu:
apk-distribute

# 3. Direct compile shortcuts:
apk-distribute --split
apk-distribute --universal
apk-distribute --debug
apk-distribute --clean-ram
```

---

## 💖 Support

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/C0C818ICQE)
