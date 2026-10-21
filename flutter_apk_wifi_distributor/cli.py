import sys
import shutil
import argparse
from pathlib import Path
from .network import get_local_ip
from .optimizer import clean_system_ram
from .core import find_built_apks, get_project_name, run_flutter_build
from .server import generate_mobile_portal_html, serve_directory

def main():
    # Windows UTF-8 stdout configuration
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="apk-distribute",
        description="Flutter APK Wi-Fi Distributor & RAM Optimizer"
    )
    parser.add_argument("--build", action="store_true", help="Compile release APKs before sharing")
    parser.add_argument("--no-split", action="store_true", help="Build single universal APK instead of split-per-abi")
    parser.add_argument("--clean-ram", action="store_true", default=True, help="Clean RAM and Gradle daemons (default: enabled)")
    parser.add_argument("--port", type=int, default=8080, help="Initial port to bind (default: 8080)")
    parser.add_argument(
        "--type",
        choices=["arm64", "arm32", "x86_64", "universal", "auto"],
        default="arm64",
        help="Target ABI to serve (default: arm64)"
    )
    args = parser.parse_args()

    project_root = Path.cwd()

    # Step 1: Optional Build
    if args.build:
        success = run_flutter_build(project_root, split_per_abi=not args.no_split)
        if not success:
            print("❌ Build failed. Aborting distribution.")
            sys.exit(1)
        print("✅ Build succeeded!")

    # Step 2: Memory reclamation
    if args.clean_ram:
        clean_system_ram(project_root)

    # Step 3: APK Discovery
    apks = find_built_apks(project_root)
    if not apks:
        print("❌ No APK found in build/ outputs. Run with --build first or build your Flutter app.")
        sys.exit(1)

    chosen_apk = apks.get(args.type) or apks.get("arm64") or list(apks.values())[0]
    apk_size_mb = chosen_apk.stat().st_size / (1024 * 1024)
    app_name = get_project_name(project_root)

    # Step 4: Staging
    staging_dir = project_root / ".apk_wifi_share"
    staging_dir.mkdir(exist_ok=True)

    target_apk_name = "app-release.apk"
    shutil.copy2(chosen_apk, staging_dir / target_apk_name)

    html_content = generate_mobile_portal_html(
        apk_filename=target_apk_name,
        apk_size_mb=apk_size_mb,
        abi_type=args.type.upper(),
        app_name=app_name
    )
    (staging_dir / "index.html").write_text(html_content, encoding="utf-8")

    # Step 5: Serve
    serve_directory(
        staging_dir=staging_dir,
        port=args.port,
        apk_name=target_apk_name,
        project_root=project_root
    )

if __name__ == "__main__":
    main()
