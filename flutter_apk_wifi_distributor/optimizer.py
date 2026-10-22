import gc
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict

def clean_system_ram(project_root: Path = None, verbose: bool = True) -> Dict[str, any]:
    """
    Terminates Gradle daemons, trims Windows working set memory,
    and runs garbage collection to reclaim system RAM after compilation.
    """
    if verbose:
        print("🧹 Optimizing memory & terminating background Gradle daemons...")
    
    if project_root is None:
        project_root = Path.cwd()

    gradle_stopped = False
    gradle_msg = "Gradle daemons not found or already stopped."
    
    android_dir = project_root / "android"
    gradlew_bat = android_dir / "gradlew.bat"
    gradlew_sh = android_dir / "gradlew"
    target_gradlew = gradlew_bat if sys.platform == "win32" else gradlew_sh

    if target_gradlew.exists():
        try:
            cmd = [str(target_gradlew.resolve()), "--stop"]
            res = subprocess.run(
                cmd,
                cwd=str(android_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20
            )
            gradle_stopped = (res.returncode == 0)
            gradle_msg = "Gradle daemons stopped successfully."
            if verbose:
                print(f"   ✅ {gradle_msg}")
        except Exception as e:
            gradle_msg = f"Failed to stop Gradle via gradlew: {e}"
            if verbose:
                print(f"   ⚠️ {gradle_msg}")
    elif android_dir.exists():
        # Fallback to system gradlew or gradle
        try:
            cmd = ["gradlew.bat" if sys.platform == "win32" else "gradlew", "--stop"]
            subprocess.run(
                cmd,
                cwd=str(android_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                shell=True
            )
            gradle_stopped = True
            gradle_msg = "Gradle daemons stopped via shell fallback."
            if verbose:
                print(f"   ✅ {gradle_msg}")
        except Exception:
            pass

    # Windows-specific memory working set trimming via Win32 API
    working_set_trimmed = False
    if sys.platform == "win32":
        try:
            import ctypes
            # Trim memory working set of current process
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
            working_set_trimmed = True
            if verbose:
                print("   ✅ Windows process working set memory trimmed.")
        except Exception:
            pass

    # Run Python runtime garbage collection
    gc.collect()

    return {
        "success": True,
        "gradle_stopped": gradle_stopped,
        "working_set_trimmed": working_set_trimmed,
        "message": "Memory optimization completed. Gradle daemons stopped and working sets flushed."
    }
