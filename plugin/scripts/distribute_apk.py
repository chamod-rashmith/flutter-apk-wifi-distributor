#!/usr/bin/env python3
"""
Flutter APK Wi-Fi Distributor & RAM Optimizer
Automates building Flutter split APKs, universal release, or debug APKs,
terminating RAM-heavy Gradle daemons, and serving the APKs over local Wi-Fi
with an instant mobile-friendly download portal and in-portal build triggers.
"""

import os
import sys
import gc
import json
import time
import socket
import shutil
import argparse
import datetime
import threading
import subprocess
from pathlib import Path
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Reconfigure stdout/stderr on Windows to prevent cp1252 emoji charmap encoding errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BUILD_TARGETS = {
    "split": {
        "name": "Split APKs (Release)",
        "cmd": ["flutter", "build", "apk", "--split-per-abi", "--release"],
        "description": "Compiles separate arm64-v8a, armeabi-v7a, and x86_64 APKs (~60% smaller download size).",
        "badge": "⚡ Recommended"
    },
    "universal": {
        "name": "Universal Release APK",
        "cmd": ["flutter", "build", "apk", "--release"],
        "description": "Compiles a single fat APK containing binaries for all CPU architectures.",
        "badge": "📦 Universal Fat APK"
    },
    "debug": {
        "name": "Debug APK",
        "cmd": ["flutter", "build", "apk", "--debug"],
        "description": "Compiles a quick debug APK with debugging tools enabled for rapid testing.",
        "badge": "🐞 Fast Debug"
    }
}

def get_local_ip() -> str:
    """Detect the active local Wi-Fi / LAN IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def clean_ram(project_root: Path = None, verbose: bool = True) -> dict:
    """Stop Gradle daemons and release unused Windows RAM working sets."""
    if verbose:
        print("🧹 Cleaning RAM and lingering Gradle daemons...")
    if project_root is None:
        project_root = Path.cwd()

    android_dir = project_root / "android"
    gradlew_bat = android_dir / "gradlew.bat"
    gradlew_sh = android_dir / "gradlew"
    target_gradlew = gradlew_bat if sys.platform == "win32" else gradlew_sh

    gradle_stopped = False
    if target_gradlew.exists():
        try:
            cmd = [str(target_gradlew.resolve()), "--stop"]
            res = subprocess.run(cmd, cwd=str(android_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            gradle_stopped = (res.returncode == 0)
            if verbose:
                print("   ✅ Gradle daemons stopped successfully.")
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Could not stop Gradle: {e}")
    elif android_dir.exists():
        try:
            cmd = ["gradlew.bat" if sys.platform == "win32" else "gradlew", "--stop"]
            subprocess.run(cmd, cwd=str(android_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, shell=True)
            gradle_stopped = True
            if verbose:
                print("   ✅ Gradle daemons stopped via shell fallback.")
        except Exception:
            pass

    # Windows-specific memory working set trimming
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
            if verbose:
                print("   ✅ Windows memory working set trimmed.")
        except Exception:
            pass

    gc.collect()
    return {"success": True, "gradle_stopped": gradle_stopped, "message": "Gradle daemons stopped and memory working set flushed."}

def get_project_name(project_root: Path) -> str:
    pubspec = project_root / "pubspec.yaml"
    if pubspec.exists():
        try:
            for line in pubspec.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("name:"):
                    return line.split(":", 1)[1].strip().replace("_", " ").title()
        except Exception:
            pass
    return project_root.resolve().name.replace("_", " ").title()

def parse_apk_metadata(apk_file: Path) -> dict:
    stat = apk_file.stat()
    size_mb = round(stat.st_size / (1024 * 1024), 2)
    mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    filename = apk_file.name
    fname_low = filename.lower()

    if "arm64" in fname_low or "v8a" in fname_low:
        abi = "arm64-v8a"
        title = "ARM64 Split APK"
        badge = "⚡ 64-bit Modern"
        is_recommended = True
    elif "armeabi" in fname_low or "v7a" in fname_low:
        abi = "armeabi-v7a"
        title = "ARMv7 Split APK"
        badge = "📱 32-bit Legacy"
        is_recommended = False
    elif "x86_64" in fname_low:
        abi = "x86_64"
        title = "x86_64 Split APK"
        badge = "💻 Emulator / Tablet"
        is_recommended = False
    elif "debug" in fname_low:
        abi = "Universal (Debug)"
        title = "Debug APK"
        badge = "🐞 Fast Debug"
        is_recommended = False
    else:
        abi = "Universal (All ABIs)"
        title = "Universal Release APK"
        badge = "📦 Fat Release APK"
        is_recommended = False

    return {
        "filename": filename,
        "path": str(apk_file),
        "size_mb": size_mb,
        "modified": mod_time,
        "mtime": stat.st_mtime,
        "abi": abi,
        "title": title,
        "badge": badge,
        "is_recommended": is_recommended,
        "download_url": f"/download/{filename}"
    }

def find_built_apks(project_root: Path) -> list:
    search_dirs = [
        project_root / "build" / "app" / "outputs" / "flutter-apk",
        project_root / "build" / "app" / "outputs" / "apk" / "release",
        project_root / "build" / "app" / "outputs" / "apk" / "debug",
        project_root / ".apk_wifi_share"
    ]
    discovered = {}
    for d in search_dirs:
        if d.exists():
            for apk_path in d.glob("*.apk"):
                if apk_path.is_file() and apk_path.stat().st_size > 0:
                    if apk_path.name not in discovered or "build" in str(apk_path):
                        discovered[apk_path.name] = apk_path

    apks = [parse_apk_metadata(path) for path in discovered.values()]
    apks.sort(key=lambda x: (not x["is_recommended"], -x["mtime"]))
    return apks

def stage_apks(project_root: Path, staging_dir: Path) -> list:
    staging_dir.mkdir(parents=True, exist_ok=True)
    source_dirs = [
        project_root / "build" / "app" / "outputs" / "flutter-apk",
        project_root / "build" / "app" / "outputs" / "apk" / "release",
        project_root / "build" / "app" / "outputs" / "apk" / "debug",
    ]
    for s_dir in source_dirs:
        if s_dir.exists():
            for f in s_dir.glob("*.apk"):
                if f.is_file() and f.stat().st_size > 0:
                    dest = staging_dir / f.name
                    if not dest.exists() or dest.stat().st_mtime < f.stat().st_mtime:
                        shutil.copy2(f, dest)

    all_staged = list(staging_dir.glob("*.apk"))
    if all_staged:
        fav = None
        for a in all_staged:
            if "arm64" in a.name.lower():
                fav = a
                break
            elif "release" in a.name.lower() and a.name != "app-release.apk":
                fav = a
        if fav and fav.name != "app-release.apk":
            try:
                shutil.copy2(fav, staging_dir / "app-release.apk")
            except Exception:
                pass
    return find_built_apks(project_root)

def run_flutter_build(project_root: Path, target: str = "split", log_callback=None):
    target_config = BUILD_TARGETS.get(target, BUILD_TARGETS["split"])
    cmd = list(target_config["cmd"])
    use_shell = (sys.platform == "win32")
    if sys.platform == "win32":
        flutter_bin = shutil.which("flutter.bat") or shutil.which("flutter") or "flutter"
        cmd[0] = flutter_bin

    header = f"⚙️ Running Flutter build: {' '.join(cmd)}\n"
    if log_callback:
        log_callback(header)
    else:
        print(header, end="")

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            shell=use_shell
        )
    except Exception as e:
        err_msg = f"\n❌ Failed to launch Flutter build process: {e}\n"
        if log_callback:
            log_callback(err_msg)
        else:
            print(err_msg)
        return False, err_msg

    full_output = []
    if process.stdout:
        for line in iter(process.stdout.readline, ""):
            full_output.append(line)
            if log_callback:
                log_callback(line)
            else:
                sys.stdout.write(line)
                sys.stdout.flush()

    process.wait()
    success = (process.returncode == 0)
    status_msg = "\n✅ Build completed successfully!\n" if success else f"\n❌ Build failed with exit code {process.returncode}\n"
    if log_callback:
        log_callback(status_msg)
    else:
        print(status_msg)
    return success, "".join(full_output)

class BuildManager:
    def __init__(self, project_root: Path, staging_dir: Path):
        self.project_root = project_root
        self.staging_dir = staging_dir
        self.is_building = False
        self.current_target = None
        self.logs = []
        self.last_error = None
        self.last_success = None
        self.last_build_time = None
        self.lock = threading.Lock()

    def append_log(self, text: str):
        with self.lock:
            self.logs.append(text)
            if len(self.logs) > 1500:
                self.logs.pop(0)

    def start_build(self, target: str) -> bool:
        with self.lock:
            if self.is_building:
                return False
            self.is_building = True
            self.current_target = target
            self.logs = [f"🚀 Initiated build for '{target}' at {datetime.datetime.now().strftime('%H:%M:%S')}\n"]
            self.last_error = None
            self.last_success = None

        t = threading.Thread(target=self._run_build_thread, args=(target,), daemon=True)
        t.start()
        return True

    def _run_build_thread(self, target: str):
        try:
            success, _ = run_flutter_build(self.project_root, target=target, log_callback=self.append_log)
            with self.lock:
                if success:
                    self.last_success = f"Build succeeded for {target}! RAM optimization initiated."
                    self.last_build_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                else:
                    self.last_error = f"Build failed for {target}."
        except Exception as e:
            with self.lock:
                self.last_error = f"Unexpected error: {e}"
                self.append_log(f"❌ Exception: {e}\n")
        finally:
            self.append_log("🧹 Reclaiming system RAM & terminating Gradle daemons...\n")
            ram_res = clean_ram(self.project_root, verbose=False)
            self.append_log(f"   {ram_res.get('message', 'RAM optimized')}\n")
            self.append_log("📦 Staging freshly built APKs for Wi-Fi download...\n")
            stage_apks(self.project_root, self.staging_dir)
            self.append_log("✅ Ready for download!\n")
            with self.lock:
                self.is_building = False

    def get_status(self) -> dict:
        with self.lock:
            return {
                "isBuilding": self.is_building,
                "currentTarget": self.current_target,
                "lastError": self.last_error,
                "lastSuccess": self.last_success,
                "lastBuildTime": self.last_build_time,
                "logCount": len(self.logs),
                "recentLogs": "".join(self.logs[-200:])
            }

def generate_mobile_portal_html(project_name: str, local_ip: str, port: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{project_name} - Wi-Fi APK Portal</title>
    <style>
        :root {{
            --bg-base: #090d16;
            --bg-card: #131c2e;
            --bg-card-subtle: #1a253c;
            --border-color: #24324d;
            --accent-primary: #3b82f6;
            --accent-emerald: #10b981;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }}
        body {{ background: var(--bg-base); color: var(--text-main); min-height: 100vh; padding: 20px 16px 40px; display: flex; flex-direction: column; align-items: center; }}
        .container {{ max-width: 520px; width: 100%; display: flex; flex-direction: column; gap: 20px; }}
        .header-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 24px; padding: 24px 20px; text-align: center; box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.6); position: relative; overflow: hidden; }}
        .header-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #3b82f6, #06b6d4, #10b981); }}
        .icon-banner {{ width: 72px; height: 72px; background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%); border-radius: 20px; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 34px; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.35); }}
        h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 6px; }}
        .network-pill {{ display: inline-flex; align-items: center; gap: 6px; background: #1e293b; color: #38bdf8; font-size: 13px; font-weight: 600; padding: 6px 14px; border-radius: 20px; border: 1px solid #334155; margin-top: 8px; }}
        .pulse-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.4; transform: scale(0.85); }} }}
        .section-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 22px; padding: 20px; display: flex; flex-direction: column; gap: 16px; }}
        .section-header {{ display: flex; align-items: center; justify-content: space-between; }}
        .section-title {{ font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
        .target-options {{ display: flex; flex-direction: column; gap: 10px; }}
        .target-label {{ display: flex; align-items: flex-start; gap: 12px; background: var(--bg-card-subtle); border: 1.5px solid var(--border-color); border-radius: 16px; padding: 14px; cursor: pointer; transition: all 0.2s ease; }}
        .target-label.selected {{ border-color: #3b82f6; background: rgba(59, 130, 246, 0.12); }}
        .target-radio {{ margin-top: 3px; accent-color: #3b82f6; transform: scale(1.15); }}
        .target-info {{ display: flex; flex-direction: column; gap: 3px; flex: 1; }}
        .target-name {{ font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
        .badge-tag {{ font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
        .badge-tag.rec {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .target-desc {{ font-size: 12px; color: var(--text-muted); line-height: 1.35; }}
        .btn-action {{ display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 16px 20px; border-radius: 16px; font-size: 16px; font-weight: 700; cursor: pointer; border: none; transition: all 0.18s ease; text-decoration: none; }}
        .btn-action:active {{ transform: scale(0.98); }}
        .btn-build {{ background: linear-gradient(135deg, #2563eb, #3b82f6); color: #ffffff; box-shadow: 0 8px 18px rgba(37, 99, 235, 0.35); }}
        .btn-build:disabled {{ background: #334155; color: #94a3b8; cursor: not-allowed; box-shadow: none; transform: none; }}
        .btn-ram {{ background: #1e293b; color: #cbd5e1; border: 1px solid #334155; font-size: 14px; padding: 12px; }}
        .apk-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .apk-card {{ background: var(--bg-card-subtle); border: 1px solid var(--border-color); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }}
        .apk-meta {{ display: flex; justify-content: space-between; align-items: flex-start; }}
        .apk-title-box {{ display: flex; flex-direction: column; gap: 4px; }}
        .apk-title {{ font-size: 15px; font-weight: 700; }}
        .apk-subtitle {{ font-size: 12px; color: var(--text-muted); }}
        .apk-badges {{ display: flex; gap: 6px; }}
        .apk-badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 8px; background: #1e293b; border: 1px solid #334155; color: #cbd5e1; }}
        .btn-download {{ background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; font-size: 15px; padding: 14px; box-shadow: 0 6px 14px rgba(16, 185, 129, 0.3); }}
        .log-box {{ background: #050811; border: 1px solid #1e293b; border-radius: 14px; padding: 12px; font-family: monospace; font-size: 11px; color: #a7f3d0; max-height: 220px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; display: none; }}
        .log-box.visible {{ display: block; }}
        .toggle-logs {{ font-size: 12px; color: #60a5fa; cursor: pointer; text-align: right; padding: 4px 0; user-select: none; }}
        .toast {{ position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: #1e293b; color: #ffffff; border: 1px solid #3b82f6; padding: 12px 24px; border-radius: 30px; font-size: 14px; font-weight: 600; box-shadow: 0 10px 25px rgba(0,0,0,0.5); opacity: 0; pointer-events: none; transition: opacity 0.3s ease; z-index: 1000; }}
        .toast.show {{ opacity: 1; }}
        .empty-placeholder {{ text-align: center; padding: 24px 12px; color: var(--text-muted); font-size: 13px; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-card">
            <div class="icon-banner">🚀</div>
            <h1 id="app-title">{project_name}</h1>
            <p style="font-size: 13px; color: var(--text-muted);">Direct Local Wi-Fi APK Distributor & RAM Optimizer</p>
            <div class="network-pill">
                <span class="pulse-dot"></span>
                <span id="network-addr">http://{local_ip}:{port}</span>
            </div>
        </div>

        <div class="section-card">
            <div class="section-header">
                <div class="section-title"><span>⚡</span> Choose & Build Package</div>
            </div>
            <div class="target-options">
                <label class="target-label selected" onclick="selectTarget('split', this)">
                    <input type="radio" name="target" value="split" class="target-radio" checked>
                    <div class="target-info">
                        <div class="target-name">Split APKs (Release) <span class="badge-tag rec">Recommended</span></div>
                        <div class="target-desc">Compiles arm64-v8a, armeabi-v7a, and x86_64 (~60% smaller file size).</div>
                    </div>
                </label>

                <label class="target-label" onclick="selectTarget('universal', this)">
                    <input type="radio" name="target" value="universal" class="target-radio">
                    <div class="target-info">
                        <div class="target-name">Universal Release APK <span class="badge-tag">Single Fat APK</span></div>
                        <div class="target-desc">Single universal release APK containing binaries for all devices.</div>
                    </div>
                </label>

                <label class="target-label" onclick="selectTarget('debug', this)">
                    <input type="radio" name="target" value="debug" class="target-radio">
                    <div class="target-info">
                        <div class="target-name">Debug APK <span class="badge-tag">Fast Build</span></div>
                        <div class="target-desc">Unoptimized debug compilation with development tools enabled.</div>
                    </div>
                </label>
            </div>

            <button id="btn-build-trigger" class="btn-action btn-build" onclick="triggerBuild()">
                <span>🔨</span> Build Selected Package & Optimize RAM
            </button>

            <div>
                <div class="toggle-logs" onclick="toggleLogs()">📜 Toggle Build Terminal Logs</div>
                <div id="log-box" class="log-box"></div>
            </div>
        </div>

        <div class="section-card">
            <div class="section-header">
                <div class="section-title"><span>⬇️</span> Available Packages</div>
                <span id="apk-count" class="badge-tag" style="background:#1e293b; color:#cbd5e1;">0 Packages</span>
            </div>
            <div id="apk-container" class="apk-list">
                <div class="empty-placeholder">
                    No APKs built yet.<br>Select a package above and tap <b>Build</b> to generate downloadable APKs!
                </div>
            </div>
        </div>

        <div class="section-card">
            <button class="btn-action btn-ram" onclick="triggerCleanRam()">
                <span>🧹</span> Stop Gradle Daemons & Free System RAM Now
            </button>
        </div>
    </div>

    <div id="toast" class="toast">Action completed</div>

    <script>
        let selectedTarget = 'split';
        let isBuilding = false;

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3500);
        }}

        function selectTarget(target, el) {{
            selectedTarget = target;
            document.querySelectorAll('.target-label').forEach(lbl => lbl.classList.remove('selected'));
            el.classList.add('selected');
            el.querySelector('input').checked = true;
        }}

        function toggleLogs() {{
            const b = document.getElementById('log-box');
            b.classList.toggle('visible');
        }}

        async function triggerBuild() {{
            if (isBuilding) return;
            const btn = document.getElementById('btn-build-trigger');
            btn.disabled = true;
            btn.innerHTML = '<span>⏳</span> Compiling... Please wait';
            
            const logBox = document.getElementById('log-box');
            logBox.classList.add('visible');
            logBox.innerText = 'Initiating compilation...\\n';

            try {{
                const res = await fetch('/api/build', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ target: selectedTarget }})
                }});
                const data = await res.json();
                if (data.status === 'started') {{
                    showToast('🚀 Compilation started! Gradle RAM will be freed after build.');
                    pollStatus();
                }} else {{
                    showToast('⚠️ ' + (data.message || 'Error starting build'));
                }}
            }} catch (err) {{
                showToast('❌ Network error starting build');
                btn.disabled = false;
                btn.innerHTML = '<span>🔨</span> Build Selected Package & Optimize RAM';
            }}
        }}

        async function triggerCleanRam() {{
            showToast('🧹 Stopping Gradle daemons and trimming Windows RAM...');
            try {{
                const res = await fetch('/api/clean-ram');
                const data = await res.json();
                showToast(data.message || '✅ RAM optimized!');
            }} catch (e) {{
                showToast('⚠️ Failed to clean RAM');
            }}
        }}

        async function pollStatus() {{
            try {{
                const res = await fetch('/api/status');
                if (!res.ok) return;
                const data = await res.json();

                isBuilding = data.isBuilding;
                const btn = document.getElementById('btn-build-trigger');
                if (isBuilding) {{
                    btn.disabled = true;
                    btn.innerHTML = '<span>🔨</span> Building Flutter APK (' + (data.currentTarget || '') + ')...';
                    if (data.recentLogs) {{
                        const logBox = document.getElementById('log-box');
                        logBox.innerText = data.recentLogs;
                        logBox.scrollTop = logBox.scrollHeight;
                    }}
                    setTimeout(pollStatus, 1500);
                }} else {{
                    btn.disabled = false;
                    btn.innerHTML = '<span>🔨</span> Build Selected Package & Optimize RAM';
                    if (data.recentLogs) {{
                        const logBox = document.getElementById('log-box');
                        logBox.innerText = data.recentLogs;
                    }}
                }}

                renderApks(data.apks || []);
            }} catch (err) {{
                console.error(err);
            }}
        }}

        function renderApks(apks) {{
            const container = document.getElementById('apk-container');
            const countBadge = document.getElementById('apk-count');
            countBadge.innerText = apks.length + ' Available';

            if (!apks || apks.length === 0) {{
                container.innerHTML = `
                    <div class="empty-placeholder">
                        No APKs built yet.<br>Select a package above and tap <b>Build</b> to generate downloadable APKs!
                    </div>
                `;
                return;
            }}

            let html = '';
            apks.forEach(apk => {{
                html += `
                    <div class="apk-card">
                        <div class="apk-meta">
                            <div class="apk-title-box">
                                <div class="apk-title">${{apk.title}}</div>
                                <div class="apk-subtitle">${{apk.filename}} &bull; ${{apk.modified}}</div>
                            </div>
                            <div class="apk-badges">
                                <span class="apk-badge">${{apk.size_mb}} MB</span>
                                <span class="apk-badge">${{apk.badge}}</span>
                            </div>
                        </div>
                        <a href="${{apk.download_url}}" download class="btn-action btn-download">
                            <span>⬇️</span> Download ${{apk.abi}} (${{apk.size_mb}} MB)
                        </a>
                    </div>
                `;
            }});
            container.innerHTML = html;
        }}

        pollStatus();
        setInterval(() => {{
            if (!isBuilding) pollStatus();
        }}, 5000);
    </script>
</body>
</html>
"""

class DistributorRequestHandler(SimpleHTTPRequestHandler):
    build_manager: BuildManager = None
    project_root: Path = None
    staging_dir: Path = None
    local_ip: str = "127.0.0.1"
    port: int = 8080

    def _send_bytes(self, data: bytes, content_type: str = "application/json", status: int = HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj: dict, status: int = HTTPStatus.OK):
        data = json.dumps(obj).encode("utf-8")
        self._send_bytes(data, content_type="application/json; charset=utf-8", status=status)

    def _send_html(self, html_str: str, status: int = HTTPStatus.OK):
        data = html_str.encode("utf-8")
        self._send_bytes(data, content_type="text/html; charset=utf-8", status=status)

    def log_message(self, format, *args):
        if len(args) > 0 and "/api/status" in str(args[0]):
            return
        super().log_message(format, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ["/", "/index.html"]:
            project_name = get_project_name(self.project_root)
            html = generate_mobile_portal_html(project_name, self.local_ip, self.port)
            self._send_html(html)
            return

        if path == "/api/status":
            status = self.build_manager.get_status()
            status["projectName"] = get_project_name(self.project_root)
            status["localIp"] = self.local_ip
            status["port"] = self.port
            status["apks"] = find_built_apks(self.project_root)
            self._send_json(status)
            return

        if path == "/api/clean-ram":
            ram_res = clean_ram(self.project_root, verbose=False)
            self._send_json(ram_res)
            return

        if path.startswith("/download/"):
            filename = path.replace("/download/", "").strip()
            self._serve_apk_file(filename)
            return

        if path.endswith(".apk"):
            filename = Path(path).name
            self._serve_apk_file(filename)
            return

        super().do_GET()

    def _serve_apk_file(self, filename: str):
        target_file = self.staging_dir / filename
        if not target_file.exists():
            for apk in find_built_apks(self.project_root):
                if apk["filename"] == filename:
                    target_file = Path(apk["path"])
                    break

        if not target_file.exists() or not target_file.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, f"APK file '{filename}' not found.")
            return

        try:
            file_size = target_file.stat().st_size
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.android.package-archive")
            self.send_header("Content-Disposition", f'attachment; filename="{target_file.name}"')
            self.send_header("Content-Length", str(file_size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with open(target_file, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/build":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            try:
                data = json.loads(body)
            except Exception:
                data = {}

            target = data.get("target", "split")
            if target not in BUILD_TARGETS:
                target = "split"

            started = self.build_manager.start_build(target)
            if started:
                resp = {"status": "started", "target": target, "message": f"Build initiated for {target}"}
            else:
                resp = {"status": "error", "message": "A build is already running in background"}
            self._send_json(resp)
            return

        if path == "/api/clean-ram":
            ram_res = clean_ram(self.project_root, verbose=False)
            self._send_json(ram_res)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found.")

def interactive_cli_menu(project_root: Path) -> str:
    app_name = get_project_name(project_root)
    existing_apks = find_built_apks(project_root)

    print("\n" + "=" * 68)
    print("🚀 FLUTTER APK WI-FI DISTRIBUTOR & RAM OPTIMIZER")
    print("=" * 68)
    print(f"📦 Project        : {app_name}")
    if existing_apks:
        print(f"📁 Available APKs : {len(existing_apks)} package(s) detected")
    print("=" * 68)
    print("\nSelect an action:")
    print("  [1] ⚡ Build Split APKs (arm64, arm32, x86_64) & Launch Server  [Recommended]")
    print("  [2] 📦 Build Universal Release APK (Fat APK) & Launch Server")
    print("  [3] 🐞 Build Debug APK & Launch Server")
    print("  [4] 🌐 Launch Server Immediately (Select & Build from Mobile Web Portal)")
    print("  [5] 🧹 Stop Gradle Daemons & Reclaim Windows RAM Only")
    print("  [0] ❌ Exit\n")

    try:
        choice = input("Enter choice [1-5] (default: 4): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        sys.exit(0)

    return choice if choice else "4"

def serve_portal(project_root: Path, port: int = 8080):
    local_ip = get_local_ip()
    staging_dir = project_root / ".apk_wifi_share"
    staging_dir.mkdir(parents=True, exist_ok=True)
    stage_apks(project_root, staging_dir)
    app_name = get_project_name(project_root)

    build_manager = BuildManager(project_root=project_root, staging_dir=staging_dir)
    DistributorRequestHandler.build_manager = build_manager
    DistributorRequestHandler.project_root = project_root
    DistributorRequestHandler.staging_dir = staging_dir
    DistributorRequestHandler.local_ip = local_ip

    server = None
    actual_port = port
    for p in range(port, port + 30):
        try:
            DistributorRequestHandler.port = p
            server = ThreadingHTTPServer(("0.0.0.0", p), DistributorRequestHandler)
            actual_port = p
            break
        except OSError:
            continue

    if not server:
        print(f"❌ Error: Unable to bind to any port in range {port}..{port+30}")
        return

    existing_apks = find_built_apks(project_root)

    print("\n" + "=" * 68)
    print("🚀 FLUTTER APK WI-FI DISTRIBUTION SERVER ONLINE")
    print("=" * 68)
    print(f"📦 Flutter Project   : {app_name}")
    print(f"📱 Phone Portal URL  : http://{local_ip}:{actual_port}")
    if existing_apks:
        print(f"⬇️ Direct Download   : http://{local_ip}:{actual_port}{existing_apks[0]['download_url']}")
        print(f"   (Detected {len(existing_apks)} existing APK package(s))")
    else:
        print("ℹ️  No compiled APKs found yet.")
        print("👉 You can select & trigger compilation directly from the Mobile Web Portal!")
    print("=" * 68)
    print("👉 Open the Phone Portal URL on your mobile browser (connected to same Wi-Fi).")
    print("👉 Press Ctrl+C in this terminal when finished to stop & free memory.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
    finally:
        server.server_close()
        clean_ram(project_root)
        print("✅ Shutdown complete. Gradle daemons stopped and memory freed.")

def main():
    parser = argparse.ArgumentParser(description="Flutter APK Wi-Fi Distributor & RAM Optimizer")
    parser.add_argument("--build", nargs="?", const="split", choices=["split", "universal", "debug"], help="Build target before serving")
    parser.add_argument("--split", action="store_true", help="Compile split APKs")
    parser.add_argument("--universal", action="store_true", help="Compile universal release APK")
    parser.add_argument("--debug", action="store_true", help="Compile debug APK")
    parser.add_argument("--server", action="store_true", help="Start server without compiling first")
    parser.add_argument("--clean-ram", action="store_true", help="Clean RAM and Gradle daemons without starting server")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    args, _ = parser.parse_known_args()

    project_root = Path.cwd()

    if args.clean_ram and not args.build and not args.server and not args.split and not args.universal and not args.debug:
        clean_ram(project_root)
        print("✅ Memory cleaned.")
        return

    chosen_target = None
    if args.split:
        chosen_target = "split"
    elif args.universal:
        chosen_target = "universal"
    elif args.debug:
        chosen_target = "debug"
    elif args.build:
        chosen_target = args.build

    if chosen_target is None and not args.server:
        if sys.stdin.isatty():
            choice = interactive_cli_menu(project_root)
            if choice == "1":
                chosen_target = "split"
            elif choice == "2":
                chosen_target = "universal"
            elif choice == "3":
                chosen_target = "debug"
            elif choice == "4":
                chosen_target = None
            elif choice == "5":
                clean_ram(project_root)
                print("✅ Memory cleaned.")
                return
            elif choice == "0":
                print("Exiting.")
                return
            else:
                chosen_target = None
        else:
            chosen_target = None

    if chosen_target:
        print(f"\n⚙️ Compiling Flutter target '{chosen_target}'...")
        success, _ = run_flutter_build(project_root, target=chosen_target)
        if not success:
            print("❌ Flutter build failed.")
            sys.exit(1)
        print("✅ Build complete!")
        clean_ram(project_root)

    serve_portal(project_root, args.port)

if __name__ == "__main__":
    main()
