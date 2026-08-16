import json
import os
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "admin_backend"
os.environ.update({
    "TEAMSPIRIT_ONLINE": "1",
    "TEAMSPIRIT_ADMIN_USERNAME": "admin",
    "TEAMSPIRIT_ADMIN_PASSWORD": "test-password-only",
})
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

import server  # noqa: E402


httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{httpd.server_port}"


def request(path, method="GET", payload=None, token=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, data=body, headers=headers, method=method)) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


try:
    status, data = request("/api/site")
    assert status == 401 and data["ok"] is False
    status, data = request("/api/auth/login", "POST", {"username": "admin", "password": "wrong"})
    assert status == 401
    status, data = request("/api/auth/login", "POST", {"username": "admin", "password": "test-password-only"})
    assert status == 200 and data["ok"] and data["token"]
    token = data["token"]
    status, data = request("/api/auth/me", token=token)
    assert status == 200 and data["authenticated"] is True
    status, data = request("/api/site", token=token)
    assert status == 200 and isinstance(data.get("products"), list)
    print("test_admin_backend.py: PASS")
finally:
    httpd.shutdown()
    httpd.server_close()
