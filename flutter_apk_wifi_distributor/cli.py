import sys
import shutil
import argparse
from pathlib import Path

from .network import get_local_ip
from .optimizer import clean_system_ram
from .core import BUILD_TARGETS, find_built_apks, get_project_name, run_flutter_build, stage_apks
from .server import serve_portal

def configure_windows_utf8():
    """Configure UTF-8 encoding for standard streams on Windows."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def interactive_menu(project_root: Path) -> str:
    """Display an interactive CLI prompt to choose the desired action."""
    app_name = get_project_name(project_root)
    existing_apks = find_built_apks(project_root)

    print("\n" + "=" * 68)
    print("🚀 FLUTTER APK WI-FI DISTRIBUTOR & RAM OPTIMIZER")
    print("=" * 68)
    print(f"📦 Active Project : {app_name}")
    if existing_apks:
        print(f"📁 Existing APKs  : {len(existing_apks)} package(s) ready in build cache")
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

    if not choice:
        return "4"
    return choice

def main():
    configure_windows_utf8()

    parser = argparse.ArgumentParser(
        prog="apk-distribute",
        description="Flutter APK Wi-Fi Distributor & Windows RAM Optimizer"
    )
    parser.add_argument(
        "--build",
        nargs="?",
        const="split",
        choices=["split", "universal", "debug", "bundle"],
        help="Compile target package before sharing (default target: split)"
    )
    parser.add_argument("--split", action="store_true", help="Shortcut to build split-per-abi APKs")
    parser.add_argument("--universal", action="store_true", help="Shortcut to build universal release APK")
    parser.add_argument("--debug", action="store_true", help="Shortcut to build debug APK")
    parser.add_argument("--server", action="store_true", help="Launch server directly without compiling first")
    parser.add_argument("--clean-ram", action="store_true", help="Stop Gradle daemons & trim memory without launching server")
    parser.add_argument("--port", type=int, default=8080, help="Initial port to bind (default: 8080)")
    
    args, unknown = parser.parse_known_args()
    project_root = Path.cwd()

    # If only RAM cleaning requested
    if args.clean_ram and not args.build and not args.server and not args.split and not args.universal and not args.debug:
        clean_system_ram(project_root)
        print("✅ Memory cleaned.")
        return

    # Determine build target from flags
    chosen_build_target = None
    if args.split:
        chosen_build_target = "split"
    elif args.universal:
        chosen_build_target = "universal"
    elif args.debug:
        chosen_build_target = "debug"
    elif args.build:
        chosen_build_target = args.build

    # If no flags passed, check if interactive terminal
    if chosen_build_target is None and not args.server:
        if sys.stdin.isatty():
            choice = interactive_menu(project_root)
            if choice == "1":
                chosen_build_target = "split"
            elif choice == "2":
                chosen_build_target = "universal"
            elif choice == "3":
                chosen_build_target = "debug"
            elif choice == "4":
                chosen_build_target = None  # Launch server directly
            elif choice == "5":
                clean_system_ram(project_root)
                print("✅ Memory cleaned.")
                return
            elif choice == "0":
                print("Exiting.")
                return
            else:
                print("Invalid choice, defaulting to launching server.")
                chosen_build_target = None
        else:
            # Non-interactive default: launch server directly
            chosen_build_target = None

    # Step 1: Pre-build if chosen
    if chosen_build_target:
        print(f"\n⚙️ Starting Flutter compilation: target = '{chosen_build_target}'...")
        success, _ = run_flutter_build(project_root, target=chosen_build_target)
        if not success:
            print(f"❌ Build failed for target '{chosen_build_target}'.")
            sys.exit(1)
        print("✅ Build completed successfully!")

        # Step 2: Memory reclamation after compilation
        clean_system_ram(project_root)

    # Step 3: Launch Wi-Fi Distribution Portal
    serve_portal(project_root=project_root, port=args.port)

if __name__ == "__main__":
    main()
