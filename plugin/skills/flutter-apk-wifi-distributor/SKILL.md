---
name: flutter-apk-wifi-distributor
description: >-
  Launches an embedded Wi-Fi distribution server allowing developers to select, compile (split-per-abi, universal release, or debug), optimize Windows/macOS/Linux RAM by terminating lingering Gradle daemons, and download Flutter APKs directly to mobile devices over local Wi-Fi. Trigger this skill whenever the user asks to build an APK, share an APK to mobile/phone over Wi-Fi, run the distribution server, clean Gradle memory, or test Flutter apps on physical devices without USB cables.
---

# Flutter APK Wi-Fi Distributor & RAM Optimizer

This skill provides an automated, cross-platform workflow for Flutter developers and AI coding agents to compile APKs, immediately reclaim system RAM (by terminating background Gradle daemons and trimming process working sets), and host an embedded mobile download portal over the local Wi-Fi network.

## Key Capabilities

1. **Launch Server First & Choose Package On Demand:**
   The distribution server can be started first without compiling beforehand. Developers can select their desired package from the mobile web dashboard (or CLI prompt):
   - ⚡ **Split APKs (Release):** Compiles `arm64-v8a`, `armeabi-v7a`, and `x86_64` (cuts download size by ~60%).
   - 📦 **Universal Release APK:** Single fat APK supporting all device architectures.
   - 🐞 **Debug APK:** Fast unoptimized compilation for quick testing.
2. **Automated RAM Reclamation:**
   Android Gradle compilation leaves behind background daemons that hold 4 GB – 8 GB+ of RAM hostage. This skill automatically executes `.\gradlew --stop`, trims process working sets, and triggers garbage collection immediately after compilation and upon server shutdown.
3. **Multi-Package Wi-Fi Download Portal:**
   Auto-detects the machine's local IPv4 Wi-Fi address (e.g. `192.168.x.x`) and hosts an embedded, dark-mode, mobile-first web app on port `8080` (with automatic port conflict fallback). All available APKs are displayed with architecture badges, file sizes, and 1-tap download buttons.
4. **Interactive In-Portal & Background Compilation:**
   Developers can trigger builds directly from their phone browser with live terminal logs streaming to the UI.

---

## Agent Instructions & Execution Flow

When a user requests to build an APK, share an APK over Wi-Fi, or clean memory, follow these steps:

### Step 1: Preflight Verification
Confirm that the current workspace or target directory is a Flutter project containing `pubspec.yaml` and an `android/` directory:
```powershell
Test-Path pubspec.yaml; Test-Path android
```

### Step 2: Determine Execution Command
Select the command based on user intent:

- **Launch Server First (User chooses or builds on-demand via web portal):**
  ```bash
  apk-distribute --server
  ```
  *(Or fallback if `apk-distribute` is not globally installed:)*
  ```powershell
  python "$HOME\.gemini\config\plugins\flutter-apk-wifi-distributor\scripts\distribute_apk.py" --server
  ```

- **Compile Split APKs and Launch Server (Default / Recommended):**
  ```bash
  apk-distribute --split
  ```

- **Compile Universal Release APK and Launch Server:**
  ```bash
  apk-distribute --universal
  ```

- **Compile Debug APK and Launch Server:**
  ```bash
  apk-distribute --debug
  ```

- **Clean Gradle Daemons & Reclaim RAM Only:**
  ```bash
  apk-distribute --clean-ram
  ```

### Step 3: Run Server as Background Process
Since the Wi-Fi distribution server runs indefinitely until stopped, execute the command in the background (e.g., using `run_command` with an async timeout).

### Step 4: Share Links with Developer
Parse the detected local Wi-Fi IP and port from the server output and present clickable links to the user in chat:
- **Mobile Web Portal:** `http://<LOCAL_WIFI_IP>:<PORT>`
- **Direct Download:** `http://<LOCAL_WIFI_IP>:<PORT>/download/app-arm64-v8a-release.apk` (or `app-release.apk`)

---

## Troubleshooting & Resilience

### 1. Windows Firewall / Wi-Fi Router Client Isolation
- If the mobile phone cannot reach the portal URL, ensure Windows Firewall allows incoming connections on port `8080` for Python.
- If testing on guest/enterprise Wi-Fi networks that enforce **Access Point (AP) / Client Isolation**, connect the phone and PC to a personal mobile hotspot.

### 2. Gradle SSLHandshake Errors on Windows
If Gradle compilation fails with `SSLHandshakeException` during Crashlytics mapping file upload or Maven dependency fetching (common with Windows antivirus proxies), configure the root CA truststore in `~/.gradle/gradle.properties`:
```properties
systemProp.javax.net.ssl.trustStore=C:/Users/<USER>/.gradle/cacerts
systemProp.javax.net.ssl.trustStorePassword=changeit
```

### 3. Port Conflicts
The server automatically probes sequential ports (`8080` to `8110`) and binds to the first available port.
