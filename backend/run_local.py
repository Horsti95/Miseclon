"""Windows-friendly single-command launcher for Miseclon.

Starts Uvicorn on 0.0.0.0:8000 and opens the browser only once /api/health is ready.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _get_lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None


def _open_browser_when_ready(url: str) -> None:
    health_url = f"{url}/api/health"
    for _ in range(50):
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.25)


def main() -> None:
    host = os.environ.get("MISE_HOST", "0.0.0.0")
    port = int(os.environ.get("MISE_PORT", "8000"))
    local_url = f"http://127.0.0.1:{port}"
    lan_ip = _get_lan_ip()

    print("")
    print("========================================================")
    print("  Miseclon läuft!")
    print(f"  PC-Browser:        {local_url}")
    if lan_ip:
        print(f"  Smartphone (WLAN): http://{lan_ip}:{port}")
    print("  Beenden mit Strg+C")
    print("========================================================")
    print("")

    if os.environ.get("MISE_NO_BROWSER") != "1":
        threading.Thread(
            target=_open_browser_when_ready, args=(local_url,), daemon=True
        ).start()

    uvicorn.run("backend.app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
