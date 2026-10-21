import os
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from .network import get_local_ip
from .optimizer import clean_system_ram

def generate_mobile_portal_html(apk_filename: str, apk_size_mb: float, abi_type: str, app_name: str = "Flutter App") -> str:
    """Generate responsive dark-mode HTML download portal for mobile screens."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{app_name} - Direct Download</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            background: #090d16;
            color: #f1f5f9;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .card {{
            background: #131c2e;
            border: 1px solid #1e293b;
            border-radius: 28px;
            padding: 40px 24px;
            max-width: 420px;
            width: 100%;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
        }}
        .icon-wrapper {{
            width: 88px;
            height: 88px;
            background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
            border-radius: 24px;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 42px;
            box-shadow: 0 10px 25px rgba(79, 70, 229, 0.45);
        }}
        h1 {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
        }}
        p.subtitle {{
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 32px;
            line-height: 1.4;
        }}
        .btn-download {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 18px 24px;
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            color: #ffffff;
            text-decoration: none;
            font-size: 17px;
            font-weight: 700;
            border-radius: 18px;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.35);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .btn-download:active {{
            transform: scale(0.98);
            filter: brightness(0.95);
        }}
        .meta-container {{
            margin-top: 28px;
            padding-top: 24px;
            border-top: 1px solid #1e293b;
            display: flex;
            justify-content: center;
            gap: 12px;
        }}
        .badge {{
            background: #1e293b;
            color: #cbd5e1;
            font-size: 13px;
            font-weight: 600;
            padding: 8px 14px;
            border-radius: 12px;
            border: 1px solid #334155;
        }}
        .footer-note {{
            margin-top: 24px;
            font-size: 12px;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-wrapper">🚀</div>
        <h1>{app_name}</h1>
        <p class="subtitle">Direct Wi-Fi transfer ready. Zero mobile data used.</p>
        <a class="btn-download" href="{apk_filename}" download>
            <span>⬇️</span> Download APK
        </a>
        <div class="meta-container">
            <div class="badge">📦 {apk_size_mb:.1f} MB</div>
            <div class="badge">⚙️ {abi_type}</div>
        </div>
        <div class="footer-note">Served via flutter-apk-wifi-distributor</div>
    </div>
</body>
</html>
"""

def serve_directory(staging_dir: Path, port: int, apk_name: str, project_root: Path):
    """Start local multi-threaded HTTP server."""
    local_ip = get_local_ip()
    os.chdir(staging_dir)

    server = None
    for p in range(port, port + 30):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", p), SimpleHTTPRequestHandler)
            port = p
            break
        except OSError:
            continue

    if not server:
        print(f"❌ Error: Unable to bind port (attempted {port}..{port+30})")
        return

    print("\n" + "=" * 65)
    print("🚀 FLUTTER APK WI-FI DISTRIBUTION SERVER ONLINE")
    print("=" * 65)
    print(f"📱 Phone Portal URL : http://{local_ip}:{port}")
    print(f"⬇️ Direct Download  : http://{local_ip}:{port}/{apk_name}")
    print("=" * 65)
    print("👉 Open the URL on your mobile browser (connected to same Wi-Fi).")
    print("👉 Press Ctrl+C in this terminal when finished to stop & free memory.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
    finally:
        server.server_close()
        clean_system_ram(project_root)
        print("✅ Shutdown complete. Memory freed.")
