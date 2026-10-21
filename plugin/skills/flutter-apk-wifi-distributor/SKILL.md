---
name: flutter-apk-wifi-distributor
description: Builds Flutter split APKs, frees Windows RAM by stopping lingering Gradle daemons and trimming system working sets, and distributes the arm64-v8a APK over the local Wi-Fi network via an embedded mobile download server. Trigger this skill whenever the user asks to build an APK, share an APK to mobile/phone over Wi-Fi, or clean Gradle memory after builds.
---

# Flutter APK Wi-Fi Distributor & RAM Optimizer

This skill provides an automated workflow for Flutter developers to compile split-per-abi release APKs, immediately reclaim Windows RAM (by stopping Gradle daemons), and share the compiled APK directly to mobile devices connected to the same Wi-Fi network via an embedded HTTP server.

## Key Capabilities

1. **Split-per-ABI Build:** Compiles optimized release APKs (`arm64-v8a`, `armeabi-v7a`, `x86_64`) reducing APK size by ~60%.
2. **Automated RAM Reclamation:** Windows does not automatically free memory held by Java/Gradle workers. This skill terminates Gradle daemons (`.\gradlew --stop`) and executes system garbage collection.
3. **Local Wi-Fi File Sharing:** Detects the machine's local Wi-Fi IPv4 address (e.g. `192.168.x.x`), hosts a responsive mobile-first download UI, and serves the APK directly to the developer's phone without requiring physical cables or mobile data consumption.
4. **Resilience & Fallbacks:** Automatically handles SSLHandshake exceptions during Crashlytics mapping file upload and offers fallback cloud links if the local Wi-Fi router enforces client isolation.
