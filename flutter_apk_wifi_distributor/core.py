import sys
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

def find_built_apks(project_root: Path) -> Dict[str, Path]:
    """Inspect Flutter output directories for release APKs."""
    search_dirs = [
        project_root / "build" / "app" / "outputs" / "flutter-apk",
        project_root / "build" / "app" / "outputs" / "apk" / "release",
    ]
    apks = {}
    for d in search_dirs:
        if d.exists():
            for apk_path in d.glob("*.apk"):
                low = apk_path.name.lower()
                if "arm64" in low or "v8a" in low:
                    apks["arm64"] = apk_path
                elif "armeabi" in low or "v7a" in low:
                    apks["arm32"] = apk_path
                elif "x86_64" in low:
                    apks["x86_64"] = apk_path
                else:
                    apks.setdefault("universal", apk_path)
    return apks

def get_project_name(project_root: Path) -> str:
    """Read app name from pubspec.yaml if present."""
    pubspec = project_root / "pubspec.yaml"
    if pubspec.exists():
        try:
            for line in pubspec.read_text(encoding="utf-8").splitlines():
                if line.startswith("name:"):
                    return line.split(":", 1)[1].strip().replace("_", " ").title()
        except Exception:
            pass
    return project_root.name.replace("_", " ").title()

def run_flutter_build(project_root: Path, split_per_abi: bool = True) -> bool:
    """Execute Flutter release APK build."""
    cmd = ["flutter", "build", "apk", "--release"]
    if split_per_abi:
        cmd.append("--split-per-abi")

    print(f"⚙️ Running build: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(project_root))
    return res.returncode == 0
