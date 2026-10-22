import socket
from typing import List

def get_local_ip() -> str:
    """Detect the active local Wi-Fi / LAN IPv4 address used for default routing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to public DNS address without sending packets
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_all_ips() -> List[str]:
    """Return all non-loopback IPv4 addresses bound to this machine."""
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    primary = get_local_ip()
    if primary not in ips and not primary.startswith("127."):
        ips.insert(0, primary)
    return ips if ips else ["127.0.0.1"]
