import os
import sys
import subprocess
from pathlib import Path

def clean_system_ram(project_root: Path = None):
    """
    Terminates Gradle daemons and trims Windows memory working sets.
    Reclaims gigabytes of system RAM following Android/Flutter compilation.
    """
    print("🧹 Optimizing memory & terminating background Gradle daemons...")
    
    if project_root is None:
        project_root = Path.cwd()

    gradlew_bat = project_root / "android" / "gradlew.bat"
    gradlew_sh = project_root / "android" / "gradlew"
    
    target_gradlew = gradlew_bat if sys.platform == "win32" else gradlew_sh

    if target_gradlew.exists():
        try:
            cmd = [str(target_gradlew.resolve()), "--stop"]
            subprocess.run(
                cmd,
                cwd=str(project_root / "android"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15
            )
            print("   ✅ Gradle daemons stopped successfully.")
        except Exception as e:
            print(f"   ⚠️ Could not stop Gradle cleanly: {e}")
    else:
        # Generic gradlew fallback if android folder exists
        android_dir = project_root / "android"
        if android_dir.exists():
            try:
                subprocess.run(
                    ["gradlew", "--stop"],
                    cwd=str(android_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    shell=True
                )
                print("   ✅ Gradle daemons stopped.")
            except Exception:
                pass

    # Windows-specific memory working set trimming via Win32 API
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
            print("   ✅ Windows process working set trimmed.")
        except Exception:
            pass
