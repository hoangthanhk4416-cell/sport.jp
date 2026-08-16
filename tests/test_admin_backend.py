import json
import os
import sys
import threading
import tempfile
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
    original_root, original_request = server.SITE_ROOT, server.github_request
    calls = []
    with tempfile.TemporaryDirectory() as folder:
        server.SITE_ROOT = Path(folder)
        (server.SITE_ROOT / "index.html").write_text("<h1>atomic publish</h1>", encoding="utf-8")
        def fake_github_request(_settings, method, path, payload=None):
            calls.append((method, path, payload))
            if method == "GET" and "/git/ref/" in path:
                return {"object": {"sha": "commit-old"}}
            if method == "GET" and "/git/trees/" in path:
                return {"tree": []}
            if method == "POST" and path.endswith("/git/trees"):
                assert payload["tree"][0]["path"] == "index.html"
                assert payload["tree"][0]["content"] == "<h1>atomic publish</h1>"
                return {"sha": "tree-new"}
            if method == "POST" and path.endswith("/git/commits"):
                return {"sha": "commit-new"}
            if method == "PATCH" and "/git/refs/heads/" in path:
                assert payload == {"sha": "commit-new", "force": False}
                return {"object": {"sha": "commit-new"}}
            raise AssertionError((method, path))
        server.github_request = fake_github_request
        published = server.publish_api({"owner": "owner", "repo": "repo", "branch": "main", "token": "test"})
        assert published["uploaded"] == ["index.html"]
        assert len([item for item in calls if item[0] == "PATCH"]) == 1
    server.SITE_ROOT, server.github_request = original_root, original_request
    print("test_admin_backend.py: PASS")
finally:
    httpd.shutdown()
    httpd.server_close()
