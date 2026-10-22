import os
import sys
import shutil
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

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
    },
    "bundle": {
        "name": "App Bundle (.aab)",
        "cmd": ["flutter", "build", "appbundle", "--release"],
        "description": "Compiles Google Play Android App Bundle.",
        "badge": "🚀 Play Store"
    }
}

def get_project_name(project_root: Path) -> str:
    """Read app name from pubspec.yaml if present, or fallback to folder name."""
    pubspec = project_root / "pubspec.yaml"
    if pubspec.exists():
        try:
            for line in pubspec.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("name:"):
                    raw_name = line.split(":", 1)[1].strip()
                    return raw_name.replace("_", " ").title()
        except Exception:
            pass
    return project_root.resolve().name.replace("_", " ").title()

def parse_apk_metadata(apk_file: Path, base_url: str = "") -> Dict:
    """Analyze an APK file name, size, and timestamp to return structured metadata."""
    stat = apk_file.stat()
    size_mb = round(stat.st_size / (1024 * 1024), 2)
    mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    filename = apk_file.name
    fname_low = filename.lower()

    # Determine ABI and flavor
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

def find_built_apks(project_root: Path) -> List[Dict]:
    """Inspect Flutter output directories and staging folder for built APKs."""
    search_dirs = [
        project_root / "build" / "app" / "outputs" / "flutter-apk",
        project_root / "build" / "app" / "outputs" / "apk" / "release",
        project_root / "build" / "app" / "outputs" / "apk" / "debug",
        project_root / ".apk_wifi_share"
    ]

    discovered: Dict[str, Path] = {}
    for d in search_dirs:
        if d.exists():
            for apk_path in d.glob("*.apk"):
                # Avoid staging alias collision if real file exists
                if apk_path.is_file() and apk_path.stat().st_size > 0:
                    if apk_path.name not in discovered or "build" in str(apk_path):
                        discovered[apk_path.name] = apk_path

    apks = [parse_apk_metadata(path) for path in discovered.values()]
    # Sort: recommended first, then by modified time descending
    apks.sort(key=lambda x: (not x["is_recommended"], -x["mtime"]))
    return apks

def stage_apks(project_root: Path, staging_dir: Path) -> List[Dict]:
    """Copy freshly built APKs into the staging directory for isolated HTTP serving."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    # Locate all APKs currently in build outputs
    source_dirs = [
        project_root / "build" / "app" / "outputs" / "flutter-apk",
        project_root / "build" / "app" / "outputs" / "apk" / "release",
        project_root / "build" / "app" / "outputs" / "apk" / "debug",
    ]

    staged_any = False
    for s_dir in source_dirs:
        if s_dir.exists():
            for f in s_dir.glob("*.apk"):
                if f.is_file() and f.stat().st_size > 0:
                    dest = staging_dir / f.name
                    # Only copy if modified or not exists
                    if not dest.exists() or dest.stat().st_mtime < f.stat().st_mtime:
                        shutil.copy2(f, dest)
                        staged_any = True

    # Also maintain a default 'app-release.apk' alias for quick curl/direct links
    all_staged = list(staging_dir.glob("*.apk"))
    if all_staged:
        # Prefer arm64 or release
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

def run_flutter_build(
    project_root: Path,
    target: str = "split",
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """
    Execute Flutter compilation for the selected target.
    Streams log output lines in real-time if a callback is provided.
    """
    target_config = BUILD_TARGETS.get(target, BUILD_TARGETS["split"])
    cmd = list(target_config["cmd"])

    use_shell = (sys.platform == "win32")
    if sys.platform == "win32":
        flutter_bin = shutil.which("flutter.bat") or shutil.which("flutter") or "flutter"
        cmd[0] = flutter_bin

    header = f"⚙️ Executing Flutter Build: {' '.join(cmd)}\n"
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
