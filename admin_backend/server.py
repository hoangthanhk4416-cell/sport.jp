import base64
import ctypes
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from seo_generator import generate_seo_pages


APP_NAME = "TEAMSPIRIT-JP Workspace"
DATA_FOLDER_NAME = "TeamspiritJPEditorDataV1"
DEFAULT_REPO = {
    "owner": "hoangthanhk4416-cell",
    "repo": "sport.jp",
    "branch": "main",
    "token": "",
    "localRepo": "",
    "siteUrl": "https://teamspiritsport.jp/",
}
TEXT_EXTENSIONS = {".html", ".css", ".js", ".json", ".xml", ".txt", ".md", ".yml", ".yaml"}
MAX_BODY = 60 * 1024 * 1024
SIZE_CHART_IMAGE = "/uploads/teamspirit-jp-size-chart.png"
ONLINE_MODE = (
    os.environ.get("TEAMSPIRIT_ONLINE") == "1"
    or os.environ.get("RENDER", "").lower() == "true"
    or bool(os.environ.get("RENDER_SERVICE_ID"))
)
ADMIN_ORIGIN = os.environ.get("TEAMSPIRIT_ADMIN_ORIGIN", "https://teamspiritsport.jp").rstrip("/")
SESSION_TTL = 7 * 24 * 60 * 60


def yen_price(value, fallback):
    digits = "".join(re.findall(r"\d", str(value or "")))
    amount = int(digits) if digits else fallback
    return f"¥{amount:,}"


def bundled_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "seed"
    return Path(__file__).resolve().parent / "seed"


def prepare_root():
    seed = bundled_root()
    if getattr(sys, "frozen", False):
        preferred = Path(sys.executable).resolve().parent / DATA_FOLDER_NAME
        fallback = Path.home() / "Documents" / DATA_FOLDER_NAME
    else:
        preferred = Path(__file__).resolve().parent / "runtime"
        fallback = preferred
    for target in (preferred, fallback):
        try:
            if not target.exists():
                shutil.copytree(seed, target)
            else:
                editor_seed = seed / "editor"
                if editor_seed.exists():
                    shutil.copytree(editor_seed, target / "editor", dirs_exist_ok=True)
                # Refresh the website shell/SEO on every app update while preserving
                # the user's products, banners, links and other SITE_DATA edits.
                seed_index = seed / "site" / "index.html"
                target_index = target / "site" / "index.html"
                if seed_index.exists() and target_index.exists():
                    data_pattern = re.compile(r"<script>window\.SITE_DATA\s*=\s*(\{.*?\});</script>", re.S)
                    old_html = target_index.read_text(encoding="utf-8")
                    fresh_html = seed_index.read_text(encoding="utf-8")
                    old_data = data_pattern.search(old_html)
                    if old_data:
                        fresh_html = data_pattern.sub(
                            lambda _match: f"<script>window.SITE_DATA={old_data.group(1)};</script>",
                            fresh_html,
                            count=1,
                        )
                    target_index.write_text(fresh_html, encoding="utf-8")
                for filename in ("robots.txt", "sitemap.xml"):
                    source_file = seed / "site" / filename
                    if source_file.exists():
                        shutil.copy2(source_file, target / "site" / filename)
                seed_assets = seed / "site" / "assets"
                if seed_assets.exists():
                    shutil.copytree(seed_assets, target / "site" / "assets", dirs_exist_ok=True)
                if target_index.exists():
                    refreshed_html = target_index.read_text(encoding="utf-8")
                    refreshed_data = data_pattern.search(refreshed_html)
                    if refreshed_data:
                        generate_seo_pages(target / "site", json.loads(refreshed_data.group(1)))
            return target
        except OSError:
            continue
    raise RuntimeError(f"Không thể tạo thư mục {DATA_FOLDER_NAME}")


ROOT = prepare_root()
SITE_ROOT = ROOT / "site"
EDITOR_ROOT = ROOT / "editor"
LEGACY_SETTINGS_FILE = ROOT / "settings.json"
SETTINGS_FILE = Path(os.environ.get("LOCALAPPDATA") or ROOT) / "TEAMSPIRIT-JP Workspace" / "settings.json"
EXPORT_ROOT = ROOT / "exports"
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1AtQo4vi6nlYV3yzRPUit0iiJTmvgllGplSSfgl1aigU/edit?gid=2027998596#gid=2027998596"
DEFAULT_PANCAKE_URL = "https://pancake.vn/"
BROWSER_PROFILE = Path(os.environ.get("LOCALAPPDATA") or ROOT) / "TEAMSPIRIT-JP Workspace" / "browser-profile-v2"
LAST_APP_HEARTBEAT = 0.0


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {} if fallback is None else fallback


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


if os.name == "nt":
    ctypes.windll.crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_wchar_p, ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(DataBlob)]
    ctypes.windll.crypt32.CryptProtectData.restype = ctypes.c_bool
    ctypes.windll.crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DataBlob), ctypes.POINTER(ctypes.c_wchar_p), ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(DataBlob)]
    ctypes.windll.crypt32.CryptUnprotectData.restype = ctypes.c_bool
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p


def protect_token(token):
    token = str(token or "").strip()
    if not token:
        return ""
    if os.name != "nt":
        return base64.b64encode(token.encode("utf-8")).decode("ascii")
    raw = token.encode("utf-8")
    buffer = ctypes.create_string_buffer(raw)
    source = DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    protected = DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), "TEAMSPIRIT-JP GitHub token", None, None, None, 0, ctypes.byref(protected)):
        raise ctypes.WinError()
    try:
        return base64.b64encode(ctypes.string_at(protected.pbData, protected.cbData)).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(protected.pbData)


def unprotect_token(value):
    if not value:
        return ""
    encrypted = base64.b64decode(value)
    if os.name != "nt":
        return encrypted.decode("utf-8")
    buffer = ctypes.create_string_buffer(encrypted)
    source = DataBlob(len(encrypted), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    plain = DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(plain)):
        return ""
    try:
        return ctypes.string_at(plain.pbData, plain.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(plain.pbData)


def load_settings():
    raw = read_json(SETTINGS_FILE, {})
    if not raw and LEGACY_SETTINGS_FILE.exists():
        raw = read_json(LEGACY_SETTINGS_FILE, {})
    settings = {key: raw.get(key, value) for key, value in DEFAULT_REPO.items()}
    if raw.get("tokenProtected"):
        settings["token"] = unprotect_token(raw.get("tokenProtected"))
    if os.environ.get("GITHUB_TOKEN"):
        settings["token"] = os.environ["GITHUB_TOKEN"].strip()
    return settings


def write_settings(settings):
    stored = {key: str(settings.get(key, "")).strip() for key in DEFAULT_REPO if key != "token"}
    stored["tokenProtected"] = protect_token(settings.get("token"))
    write_json(SETTINGS_FILE, stored)


def settings_public():
    settings = dict(DEFAULT_REPO)
    settings.update(load_settings())
    safe = dict(settings)
    safe["token"] = "********" if settings.get("token") else ""
    safe["dataFolder"] = str(ROOT)
    safe["settingsFile"] = str(SETTINGS_FILE)
    return safe


def save_settings(payload):
    old = dict(DEFAULT_REPO)
    old.update(load_settings())
    clean = {key: str(payload.get(key, old.get(key, ""))).strip() for key in DEFAULT_REPO}
    if clean.get("token") == "********":
        clean["token"] = old.get("token", "")
    write_settings(clean)
    return settings_public()


def create_admin_session(username):
    payload = json.dumps({
        "sub": str(username),
        "exp": int(time.time()) + SESSION_TTL,
        "nonce": secrets.token_urlsafe(12),
    }, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(admin_session_secret_(), encoded.encode("ascii"), hashlib.sha256).digest()
    signed = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded}.{signed}"


def valid_admin_session(token):
    try:
        encoded, supplied = str(token or "").split(".", 1)
        expected = base64.urlsafe_b64encode(
            hmac.new(admin_session_secret_(), encoded.encode("ascii"), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        if not hmac.compare_digest(supplied, expected):
            return False
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        return int(payload.get("exp") or 0) > int(time.time()) and hmac.compare_digest(
            str(payload.get("sub") or ""), os.environ.get("TEAMSPIRIT_ADMIN_USERNAME", "admin")
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def revoke_admin_session(token):
    return None


def admin_session_secret_():
    secret = os.environ.get("TEAMSPIRIT_SESSION_SECRET") or os.environ.get("TEAMSPIRIT_ADMIN_PASSWORD") or ""
    return hashlib.sha256(("TEAMSPIRIT-JP:" + secret).encode("utf-8")).digest()


SITE_DATA_RE = re.compile(r"<script>window\.SITE_DATA\s*=\s*(\{.*?\});</script>", re.S)
NOTICE_OVERRIDE_RE = re.compile(r"\s*<script>window\.SITE_DATA\.topNotice\s*=\s*(.*?);</script>\s*", re.S)


def normalize_site(site):
    common_sizes = [
        {"size": "90 (S)", "length": "67", "bodyWidth": "48", "shoulder": "42", "sleeve": "19", "height": "160〜165", "weight": "50〜60"},
        {"size": "95 (M)", "length": "69", "bodyWidth": "50", "shoulder": "44", "sleeve": "20", "height": "165〜170", "weight": "60〜70"},
        {"size": "100 (L)", "length": "71", "bodyWidth": "52", "shoulder": "46", "sleeve": "21", "height": "170〜175", "weight": "70〜80"},
        {"size": "105 (XL)", "length": "73", "bodyWidth": "54", "shoulder": "48", "sleeve": "22", "height": "175〜180", "weight": "80〜90"},
        {"size": "110 (2XL)", "length": "75", "bodyWidth": "56", "shoulder": "50", "sleeve": "23", "height": "180〜185", "weight": "90〜100"},
        {"size": "115 (3XL)", "length": "77", "bodyWidth": "58", "shoulder": "52", "sleeve": "24", "height": "185〜190", "weight": "100〜110"},
        {"size": "120 (4XL)", "length": "79", "bodyWidth": "60", "shoulder": "54", "sleeve": "25", "height": "190〜195", "weight": "110〜120"},
    ]
    common_pants_sizes = [
        {"size": "S", "length": "40", "waist": "52", "hip": "64"},
        {"size": "M", "length": "42", "waist": "54", "hip": "67"},
        {"size": "L", "length": "44", "waist": "56", "hip": "69"},
        {"size": "XL", "length": "46", "waist": "58", "hip": "71"},
        {"size": "2XL", "length": "48", "waist": "60", "hip": "74"},
        {"size": "3XL", "length": "50", "waist": "62", "hip": "76"},
    ]
    defaults = {
        "brand": "TEAMSPIRIT-jp",
        "topNotice": "",
        "noticeMotion": "scroll",
        "noticeSpeed": 18,
        "defaultLINELink": "https://teamspiritsport.jp/pages/line/",
        "defaultInstagramLink": "",
        "heroImages": [],
        "shortcuts": [],
        "products": [],
        "teamKitSlides": [],
        "footerPhone": "",
    }
    for key, value in defaults.items():
        site.setdefault(key, value)

    # Canonical public product IDs use one SEO-safe TEAMSPIRIT-JP sequence.
    # Older imports used teamspirit-krXX and the first JP imports used
    # teamspirit-jp-newXX.  Resolve both forms (and pasted product names) here
    # so Team Kit slides, collections and generated URLs never lose products.
    legacy_product_ids = {}
    product_names = {}
    used_product_ids = set()
    for product in site.get("products", []):
        old_id = str(product.get("id") or "").strip()
        name = str(product.get("name") or "").strip()
        number_match = re.fullmatch(r"TEAMSPIRIT-JP\s*0*(\d+)", name, re.IGNORECASE)
        canonical_id = old_id
        if number_match:
            canonical_id = f"teamspirit-jp{int(number_match.group(1)):02d}"
        if canonical_id in used_product_ids and canonical_id != old_id:
            canonical_id = old_id
        product["id"] = canonical_id
        used_product_ids.add(canonical_id)
        if old_id:
            legacy_product_ids[old_id] = canonical_id
        if name:
            product_names[name.casefold()] = canonical_id

    def canonical_product_ref(value):
        ref = str(value or "").strip()
        return legacy_product_ids.get(ref, product_names.get(ref.casefold(), ref))

    for slide in site.get("teamKitSlides", []):
        slide["productIds"] = [canonical_product_ref(value) for value in (slide.get("productIds") or []) if str(value or "").strip()]
    for key, values in (site.get("collectionProductIds") or {}).items():
        site["collectionProductIds"][key] = [canonical_product_ref(value) for value in (values or []) if str(value or "").strip()]
    if not str(site.get("footerPhone", "")).strip("0 "):
        site["footerPhone"] = "LINEç›¸è«‡"
    if not str(site.get("footerText", "")).strip():
        site["footerText"] = "ë§žì¶¤ ì¶•êµ¬ ìœ ë‹ˆí¼Â·ë‹¨ì²´ íŒ€ë³µ ì œìž‘ ì „ë¬¸ ìŠ¤í† ì–´"
    if not isinstance(site.get("heroImages"), list):
        site["heroImages"] = []
    if not site["heroImages"] and site.get("heroImage"):
        site["heroImages"] = [site["heroImage"]]
    site["heroImage"] = site["heroImages"][0] if site["heroImages"] else ""
    for product in site.get("products", []):
        product.setdefault("gallery", [])
        product.setdefault("sizeChart", [])
        product.setdefault("pantsSizeChart", [])
        product.setdefault("collections", [])
        product.setdefault("reviews", [])
        product.setdefault("hidden", False)
        product.setdefault("lineLink", "")
        product.setdefault("instagramLink", "")
        # All products share the approved Japanese size chart as image 2.
        # Normalize prices here so saves, syncs and publishes cannot restore
        # the broken question-mark/yen text produced by older editor builds.
        product["hoverImage"] = SIZE_CHART_IMAGE
        product["price"] = yen_price(product.get("price"), 4500)
        product["oldPrice"] = yen_price(product.get("oldPrice"), 6500)
        if not isinstance(product["reviews"], list):
            product["reviews"] = []
        for review in product["reviews"]:
            try:
                review["stars"] = max(0, min(5, int(review.get("stars") or 0)))
            except (TypeError, ValueError):
                review["stars"] = 0
            review.setdefault("author", "")
            review.setdefault("date", "")
            review.setdefault("text", "")
            if not isinstance(review.get("images"), list):
                review["images"] = []
        old_price = int("".join(re.findall(r"\d", str(product.get("oldPrice") or ""))) or 0)
        current_price = int("".join(re.findall(r"\d", str(product.get("price") or ""))) or 0)
        product["sale"] = f"{round((old_price - current_price) / old_price * 100)}%" if old_price > current_price > 0 else ""
        # Never publish unfinished editor placeholders or Vietnamese template copy.
        if str(product.get("name", "")).strip() in {"Sản phẩm mới", "새 상품"}:
            product["name"] = "ìƒˆ ìƒí’ˆ"
            product["price"] = "ê°€ê²©ë¬¸ì˜"
            product["hidden"] = True
            product["homeFeatured"] = False
        rows = product.get("sizeChart")
        has_current_shirt_chart = isinstance(rows, list) and len(rows) == 7 and all(
            isinstance(row, dict) and str(row.get("bodyWidth", "")).strip() and str(row.get("sleeve", "")).strip()
            for row in rows
        )
        if not has_current_shirt_chart:
            product["sizeChart"] = [dict(row) for row in common_sizes]
        pants_rows = product.get("pantsSizeChart")
        has_current_pants_chart = isinstance(pants_rows, list) and len(pants_rows) == 6 and all(
            isinstance(row, dict) and str(row.get("waist", "")).strip() and str(row.get("hip", "")).strip()
            for row in pants_rows
        )
        if not has_current_pants_chart:
            product["pantsSizeChart"] = [dict(row) for row in common_pants_sizes]
    return site


def read_site_data():
    html = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
    match = SITE_DATA_RE.search(html)
    if not match:
        raise ValueError("Không tìm thấy window.SITE_DATA trong index.html")
    site = json.loads(match.group(1))
    override = NOTICE_OVERRIDE_RE.search(html)
    if override:
        try:
            site["topNotice"] = json.loads(override.group(1))
        except ValueError:
            pass
    return normalize_site(site)


def write_site_data(site):
    site = normalize_site(site)
    index = SITE_ROOT / "index.html"
    html = index.read_text(encoding="utf-8")
    payload = json.dumps(site, ensure_ascii=False, separators=(",", ":"))
    replacement = f"<script>window.SITE_DATA={payload};</script>"
    html, count = SITE_DATA_RE.subn(lambda _m: replacement, html, count=1)
    if not count:
        raise ValueError("Không tìm thấy vùng dữ liệu website")
    html = NOTICE_OVERRIDE_RE.sub("\n", html)
    index.write_text(html, encoding="utf-8")
    generate_seo_pages(SITE_ROOT, site)
    return site


def safe_relative(value, allow_new=False):
    value = urllib.parse.unquote(str(value or "")).replace("\\", "/").lstrip("/")
    candidate = (SITE_ROOT / value).resolve()
    root = SITE_ROOT.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Đường dẫn không hợp lệ")
    if not allow_new and not candidate.exists():
        raise FileNotFoundError(value)
    return candidate


def relative_name(path):
    return path.relative_to(SITE_ROOT).as_posix()


def list_pages():
    pages = []
    blog_root = SITE_ROOT / "blog"
    for path in sorted(blog_root.rglob("index.html")) if blog_root.exists() else []:
        if path == blog_root / "index.html":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        title = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
        heading = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)
        label = re.sub(r"<[^>]+>", "", (heading or title).group(1)).strip() if (heading or title) else path.stem
        pages.append({"path": relative_name(path), "title": label, "size": path.stat().st_size})
    return pages


def list_files():
    files = []
    for path in sorted(SITE_ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            files.append({"path": relative_name(path), "size": path.stat().st_size})
    return files


def product_slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "product"


def seo_product_report():
    site = read_site_data()
    generate_seo_pages(SITE_ROOT, site)
    sitemap_path = SITE_ROOT / "sitemap.xml"
    robots_path = SITE_ROOT / "robots.txt"
    sitemap = sitemap_path.read_text(encoding="utf-8", errors="replace") if sitemap_path.exists() else ""
    robots = robots_path.read_text(encoding="utf-8", errors="replace") if robots_path.exists() else ""
    rows = []
    for product in site.get("products", []):
        hidden = bool(product.get("hidden"))
        name = str(product.get("name") or product.get("id") or "").strip()
        image = str(product.get("image") or "").strip()
        slug = product_slug(product.get("id") or name)
        rel = f"products/{slug}/index.html"
        url = f"https://teamspiritsport.jp/products/{slug}/"
        page_path = SITE_ROOT / rel
        issues = []
        warnings = []
        if hidden:
            warnings.append("Đang ẩn trên web")
        if not name or name in {"Sản phẩm mới", "새 상품"}:
            issues.append("Tên sản phẩm chưa hoàn chỉnh")
        if not image:
            issues.append("Thiếu ảnh chính")
        if not str(product.get("price") or "").strip() or not re.search(r"\d", str(product.get("price") or "")):
            issues.append("Thiếu giá hiện tại")
        if not str(product.get("oldPrice") or "").strip() or not re.search(r"\d", str(product.get("oldPrice") or "")):
            warnings.append("Thiếu giá gốc")
        if not product.get("sizeChart"):
            warnings.append("Thiếu bảng size")
        if not hidden:
            if not page_path.exists():
                issues.append("Chưa tạo trang URL sản phẩm")
            else:
                html = page_path.read_text(encoding="utf-8", errors="replace")
                if '<script type="application/ld+json">' not in html or '"@type":"Product"' not in html:
                    issues.append("Thiếu Product schema")
                if '"shippingDetails"' not in html:
                    issues.append("Thiếu shippingDetails")
                if '"hasMerchantReturnPolicy"' not in html:
                    issues.append("Thiếu return policy")
                if f'<link rel="canonical" href="{url}">' not in html:
                    issues.append("Canonical chưa đúng")
                if 'meta name="description"' not in html:
                    issues.append("Thiếu meta description")
            if url not in sitemap:
                issues.append("URL chưa có trong sitemap")
        rows.append({
            "id": str(product.get("id") or ""),
            "name": name or str(product.get("id") or ""),
            "url": url,
            "hidden": hidden,
            "issues": issues,
            "warnings": warnings,
            "ok": not issues,
        })
    public_rows = [row for row in rows if not row["hidden"]]
    summary = {
        "totalProducts": len(rows),
        "publicProducts": len(public_rows),
        "okProducts": sum(1 for row in public_rows if row["ok"]),
        "issueProducts": sum(1 for row in public_rows if row["issues"]),
        "sitemap": "/sitemap.xml" if sitemap_path.exists() else "",
        "robotsHasSitemap": "Sitemap:" in robots,
    }
    return {"summary": summary, "products": rows}


def upload_image(payload):
    name = Path(str(payload.get("name") or "image.png")).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-") or "image.png"
    data = str(payload.get("data") or "")
    match = re.match(r"data:([\w/+.-]+);base64,(.+)", data, re.S)
    if not match:
        raise ValueError("Dữ liệu ảnh không hợp lệ")
    raw = base64.b64decode(match.group(2), validate=True)
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError("Ảnh vượt quá 20 MB")
    uploads = SITE_ROOT / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    target = uploads / f"{stamp}-{name}"
    target.write_bytes(raw)
    return "/uploads/" + target.name


def article_template(title, description, body):
    site = read_site_data()
    brand = escape(site.get("brand") or "TEAMSPIRIT-JP")
    phone = escape(site.get("footerPhone") or "")
    footer = escape(site.get("footerText") or "")
    title_e = escape(title)
    description_e = escape(description)
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_e} | {brand}</title><meta name="description" content="{description_e}"><link rel="stylesheet" href="/pages/common.css">
<style>.article{{max-width:980px;margin:0 auto;padding:54px 24px 90px}}.article h1{{font-size:34px;text-align:center;margin-bottom:14px}}.article .lead{{text-align:center;color:#777;margin-bottom:46px}}.article-body{{font-size:17px;line-height:1.9}}.article-body img{{display:block;max-width:100%;height:auto;margin:28px auto}}@media(max-width:620px){{.article{{padding:34px 18px 64px}}.article h1{{font-size:26px}}.article-body{{font-size:16px}}}}</style></head>
<body><header class="site-header"><div class="header-inner"><a class="site-brand" href="/">{brand}</a><nav><a href="/#category/products">ALL PRODUCTS</a><a href="/#category/custom">CUSTOM</a><a href="/#category/football">FOOTBALL WEAR</a><a href="/#category/teamkit">TEAM KIT</a><a href="/#category/training">TRAINING</a></nav></div></header>
<main class="article"><h1 data-editor-title>{title_e}</h1><p class="lead" data-editor-description>{description_e}</p><div class="article-body" data-editor-body>{body}</div></main>
<footer class="site-footer"><div><b>{brand}</b><p>{footer}</p></div><div><b>{phone}</b></div></footer></body></html>'''


def create_article(payload):
    slug = re.sub(r"[^a-z0-9-]+", "-", str(payload.get("slug") or "").lower()).strip("-")
    if not slug:
        raise ValueError("Cần nhập đường dẫn bài viết")
    target = safe_relative(f"blog/{slug}/index.html", allow_new=True)
    if target.exists():
        raise ValueError("Đường dẫn bài viết đã tồn tại")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(article_template(str(payload.get("title") or slug), str(payload.get("description") or ""), str(payload.get("body") or "")), encoding="utf-8")
    return relative_name(target)


def export_zip():
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    target = EXPORT_ROOT / f"teamspirit-jp-site-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in SITE_ROOT.rglob("*"):
            if path.is_file():
                archive.write(path, relative_name(path))
    return target


def run_command(args, cwd):
    completed = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "Lệnh thất bại").strip())
    return completed.stdout.strip()


def publish_local(settings):
    repo = Path(settings.get("localRepo") or "").expanduser().resolve()
    if not (repo / ".git").exists():
        raise ValueError("Thư mục repository cục bộ không hợp lệ")
    for source in SITE_ROOT.iterdir():
        if source.name == ".git":
            continue
        target = repo / source.name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    run_command(["git", "add", "-A"], repo)
    status = run_command(["git", "status", "--porcelain"], repo)
    if not status:
        return {"mode": "local", "message": "Không có thay đổi mới để đăng"}
    run_command(["git", "commit", "-m", "Update website from TEAMSPIRIT Editor"], repo)
    run_command(["git", "push", "origin", settings.get("branch") or "main"], repo)
    return {"mode": "local", "message": "Đã commit và push lên GitHub"}


def github_request(settings, method, path, payload=None):
    owner = settings.get("owner")
    repo = settings.get("repo")
    token = settings.get("token")
    if not owner or not repo or not token:
        raise ValueError("Cần owner, repository và GitHub token")
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TEAMSPIRIT-Editor",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub HTTP {exc.code}: {detail[:500]}") from exc


def git_blob_sha(content):
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def publish_api(settings):
    branch = settings.get("branch") or "main"
    owner = urllib.parse.quote(settings["owner"], safe="")
    repo = urllib.parse.quote(settings["repo"], safe="")
    encoded_branch = urllib.parse.quote(branch, safe="")
    ref = github_request(settings, "GET", f"/repos/{owner}/{repo}/git/ref/heads/{encoded_branch}")
    commit_sha = ref.get("object", {}).get("sha")
    if not commit_sha:
        raise RuntimeError("Không đọc được nhánh GitHub hiện tại")
    tree = github_request(settings, "GET", f"/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1")
    remote_files = {
        item.get("path"): item.get("sha")
        for item in tree.get("tree", [])
        if item.get("type") == "blob" and item.get("path")
    }
    uploaded = []
    skipped = []
    tree_items = []
    for path in sorted(SITE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = relative_name(path)
        content = path.read_bytes()
        sha = remote_files.get(rel)
        if sha == git_blob_sha(content):
            skipped.append(rel)
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            tree_items.append({"path": rel, "mode": "100644", "type": "blob", "content": content.decode("utf-8")})
        else:
            blob = github_request(settings, "POST", f"/repos/{owner}/{repo}/git/blobs", {
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            })
            tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob.get("sha")})
        uploaded.append(rel)
    if not uploaded:
        message = f"Không có tệp thay đổi; đã bỏ qua {len(skipped)} tệp không đổi"
    else:
        new_tree = github_request(settings, "POST", f"/repos/{owner}/{repo}/git/trees", {
            "base_tree": commit_sha,
            "tree": tree_items,
        })
        new_commit = github_request(settings, "POST", f"/repos/{owner}/{repo}/git/commits", {
            "message": f"Update {len(uploaded)} files from TEAMSPIRIT Editor",
            "tree": new_tree.get("sha"),
            "parents": [commit_sha],
        })
        github_request(settings, "PATCH", f"/repos/{owner}/{repo}/git/refs/heads/{encoded_branch}", {
            "sha": new_commit.get("sha"),
            "force": False,
        })
        message = f"Đã đăng {len(uploaded)} tệp trong 1 commit; bỏ qua {len(skipped)} tệp không đổi"
    return {"mode": "api-incremental", "message": message, "uploaded": uploaded, "skipped": skipped}


def publish_site():
    generate_seo_pages(SITE_ROOT, read_site_data())
    settings = dict(DEFAULT_REPO)
    settings.update(load_settings())
    if settings.get("localRepo") and (Path(settings["localRepo"]).expanduser() / ".git").exists():
        return publish_local(settings)
    return publish_api(settings)


def sync_site():
    settings = dict(DEFAULT_REPO)
    settings.update(load_settings())
    local = Path(settings.get("localRepo") or "").expanduser()
    if settings.get("localRepo") and (local / ".git").exists():
        run_command(["git", "pull", "--ff-only", "origin", settings.get("branch") or "main"], local)
        source = local
        mode = "local"
    else:
        owner, repo, branch = settings.get("owner"), settings.get("repo"), settings.get("branch") or "main"
        if not owner or not repo:
            raise ValueError("Cần GitHub owner và repository")
        url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{urllib.parse.quote(branch)}.zip"
        request = urllib.request.Request(url, headers={"User-Agent": "TEAMSPIRIT-Editor"})
        temp_dir = Path(tempfile.mkdtemp(prefix="teamspirit-jp-sync-"))
        archive_path = temp_dir / "repo.zip"
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                archive_path.write_bytes(response.read())
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(temp_dir)
            folders = [p for p in temp_dir.iterdir() if p.is_dir()]
            if not folders:
                raise RuntimeError("Gói GitHub không hợp lệ")
            source = folders[0]
            mode = "github-zip"
            backup = export_zip()
            if SITE_ROOT.exists():
                shutil.rmtree(SITE_ROOT)
            shutil.copytree(source, SITE_ROOT, ignore=shutil.ignore_patterns(".git"))
            return {"mode": mode, "backup": str(backup), "site": read_site_data()}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    backup = export_zip()
    if SITE_ROOT.exists():
        shutil.rmtree(SITE_ROOT)
    shutil.copytree(source, SITE_ROOT, ignore=shutil.ignore_patterns(".git"))
    return {"mode": mode, "backup": str(backup), "site": read_site_data()}


def launch_workspace_window(target_url):
    if not re.match(r"^https?://", str(target_url or ""), re.I):
        raise ValueError("Địa chỉ làm việc không hợp lệ")
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    edge_exe = next((item for item in candidates if item.is_file()), None)
    if edge_exe is None:
        raise RuntimeError("Không tìm thấy Microsoft Edge")
    profile = BROWSER_PROFILE.parent / "edge-app-profile"
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        str(edge_exe), f"--app={target_url}", f"--user-data-dir={profile}",
        "--start-maximized", "--no-first-run", "--disable-features=msEdgeSidebarV2",
    ])


class Handler(BaseHTTPRequestHandler):
    server_version = "TEAMSPIRITEditor/2.0"

    def log_message(self, _format, *_args):
        return

    def send_bytes(self, status, data, content_type="application/octet-stream", headers=None):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin", "").rstrip("/")
        if origin and hmac.compare_digest(origin, ADMIN_ORIGIN):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def serve_file(self, path):
        try:
            if not path.is_file():
                return self.send_json({"ok": False, "error": "Không tìm thấy tệp"}, 404)
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if content_type.startswith("text/") or path.suffix.lower() in {".js", ".json", ".xml"}:
                content_type += "; charset=utf-8"
            self.send_bytes(200, path.read_bytes(), content_type)
        except OSError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def parse_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("Dữ liệu gửi lên quá lớn")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def bearer_token(self):
        value = self.headers.get("Authorization", "")
        return value[7:].strip() if value.lower().startswith("bearer ") else ""

    def require_admin(self):
        if not valid_admin_session(self.bearer_token()):
            self.send_json({"ok": False, "error": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn"}, 401)
            return False
        return True

    def do_OPTIONS(self):
        self.send_bytes(204, b"")

    def do_GET(self):
        global LAST_APP_HEARTBEAT
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path in {"/", "/editor", "/editor/"}:
                return self.serve_file(EDITOR_ROOT / "index.html")
            if path.startswith("/editor/"):
                target = (EDITOR_ROOT / path[len("/editor/"):]).resolve()
                if EDITOR_ROOT.resolve() not in target.parents:
                    raise ValueError("Đường dẫn không hợp lệ")
                return self.serve_file(target)
            if path == "/api/health":
                return self.send_json({"ok": True, "name": APP_NAME, "root": str(ROOT), "sessionMode": "signed-v2"})
            if path == "/api/auth/me":
                return self.send_json({"ok": True, "authenticated": valid_admin_session(self.bearer_token())})
            if path.startswith("/api/") and not self.require_admin():
                return
            if path == "/api/heartbeat":
                LAST_APP_HEARTBEAT = time.monotonic()
                return self.send_json({"ok": True})
            if path == "/api/site":
                return self.send_json(read_site_data())
            if path == "/api/settings":
                return self.send_json(settings_public())
            if path == "/api/pages":
                return self.send_json(list_pages())
            if path == "/api/seo-report":
                return self.send_json({"ok": True, **seo_product_report()})
            if path == "/api/files":
                return self.send_json(list_files())
            if path == "/api/file":
                target = safe_relative(query.get("path", [""])[0])
                if target.suffix.lower() not in TEXT_EXTENSIONS:
                    raise ValueError("Loại tệp không được chỉnh sửa")
                return self.send_json({"path": relative_name(target), "content": target.read_text(encoding="utf-8")})
            if path == "/api/export":
                target = export_zip()
                return self.send_json({"ok": True, "path": str(target)})
            if path.startswith("/preview"):
                rel = path[len("/preview"):].lstrip("/") or "index.html"
                target = safe_relative(rel)
                if target.is_dir():
                    target = target / "index.html"
                return self.serve_file(target)
            target = safe_relative(path.lstrip("/"))
            if target.is_dir():
                target = target / "index.html"
            return self.serve_file(target)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            payload = self.parse_body()
            if path == "/api/auth/login":
                username = str(payload.get("username") or "").strip()
                password = str(payload.get("password") or "")
                expected_username = os.environ.get("TEAMSPIRIT_ADMIN_USERNAME", "admin")
                expected_password = os.environ.get("TEAMSPIRIT_ADMIN_PASSWORD", "")
                if not expected_password:
                    return self.send_json({"ok": False, "error": "Backend chưa được thiết lập mật khẩu quản trị"}, 503)
                if not hmac.compare_digest(username, expected_username) or not hmac.compare_digest(password, expected_password):
                    time.sleep(0.6)
                    return self.send_json({"ok": False, "error": "Sai tài khoản hoặc mật khẩu"}, 401)
                return self.send_json({"ok": True, "token": create_admin_session(username), "expiresIn": SESSION_TTL})
            if path == "/api/auth/logout":
                revoke_admin_session(self.bearer_token())
                return self.send_json({"ok": True})
            if path.startswith("/api/") and not self.require_admin():
                return
            if path == "/api/open-workspace":
                kind = str(payload.get("kind") or "browser")
                defaults = {"pancake": DEFAULT_PANCAKE_URL, "sheet": DEFAULT_SHEET_URL}
                target_url = str(payload.get("url") or defaults.get(kind) or "")
                launch_workspace_window(target_url)
                return self.send_json({"ok": True})
            if path == "/api/site":
                return self.send_json({"ok": True, "site": write_site_data(payload)})
            if path == "/api/settings":
                return self.send_json({"ok": True, "settings": save_settings(payload)})
            if path == "/api/upload":
                return self.send_json({"ok": True, "url": upload_image(payload)})
            if path == "/api/file":
                target = safe_relative(payload.get("path"), allow_new=True)
                if target.suffix.lower() not in TEXT_EXTENSIONS:
                    raise ValueError("Loại tệp không được chỉnh sửa")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(payload.get("content") or ""), encoding="utf-8")
                return self.send_json({"ok": True, "path": relative_name(target)})
            if path == "/api/article":
                return self.send_json({"ok": True, "path": create_article(payload)})
            if path == "/api/publish":
                return self.send_json({"ok": True, **publish_site()})
            if path == "/api/sync":
                return self.send_json({"ok": True, **sync_site()})
            return self.send_json({"ok": False, "error": "Không tìm thấy API"}, 404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)


class DesktopApi:
    """Open every work page in a WebView window owned by this EXE."""

    def __init__(self, editor_url):
        self.editor_url = editor_url
        self.windows = {}
        self.lock = threading.RLock()

    def _normalise_url(self, value):
        value = str(value or "").strip()
        if value.startswith("/"):
            value = urllib.parse.urljoin(self.editor_url, value)
        if not re.match(r"^https?://", value, re.I):
            raise ValueError("Chỉ mở địa chỉ http hoặc https")
        return value

    def _show(self, key, title, url):
        url = self._normalise_url(url)
        with self.lock:
            window = self.windows.get(key)
            if window:
                if key.startswith("browser") or key.startswith("preview"):
                    window.load_url(url)
                window.show()
                window.restore()
                return {"ok": True, "reused": True}
            window = webview.create_window(
                title,
                html=f'<!doctype html><meta charset="utf-8"><title>TEAMSPIRIT-JP</title><style>html,body{{margin:0;background:#10141c;color:white;font-family:Arial}}main{{padding:32px}}</style><main>TEAMSPIRIT-JP ã‚’èª­ã¿è¾¼ã‚“ã§ã„ã¾ã™...</main><script>location.replace("{url}")</script>',
                js_api=self,
                width=1440,
                height=920,
                min_size=(900, 620),
                resizable=True,
                maximized=True,
                text_select=True,
                zoomable=True,
            )
            self.windows[key] = window
            def forget_window():
                with self.lock:
                    if self.windows.get(key) is window:
                        self.windows.pop(key, None)
            window.events.closed += forget_window
            return {"ok": True, "reused": False}

    def open_workspace(self, kind, url=""):
        kind = str(kind or "").lower()
        if kind == "pancake":
            return self._show("pancake", "TEAMSPIRIT-JP - Pancake", DEFAULT_PANCAKE_URL)
        if kind == "sheet":
            return self._show("sheet", "TEAMSPIRIT-JP - Đơn hàng & Google Sheet", DEFAULT_SHEET_URL)
        if kind == "editor":
            return {"ok": True}
        return self._show("browser", "TEAMSPIRIT-JP - Trình duyệt", url)

    def open_url(self, url, name="browser", title="TEAMSPIRIT-JP - Trang làm việc"):
        safe_name = re.sub(r"[^a-z0-9_-]+", "-", str(name or "browser").lower()).strip("-") or "browser"
        return self._show("preview-" + safe_name, str(title or "TEAMSPIRIT-JP - Trang làm việc"), url)

def choose_port(start=4208, end=4220):
    import socket
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Không tìm thấy cổng trống từ 4208 đến 4219")


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("TEAMSPIRIT_PORT") or choose_port())
    url = f"http://127.0.0.1:{port}/editor/"
    if sys.stdout:
        print(f"TEAMSPIRIT-JP Workspace running at {url}")
    server = ThreadingHTTPServer(("0.0.0.0" if ONLINE_MODE else "127.0.0.1", port), Handler)
    if ONLINE_MODE or os.environ.get("TEAMSPIRIT_TEST") == "1":
        server.serve_forever()
    else:
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        # Wait until the local editor is serving before WebView2 navigates.
        last_start_error = None
        for _attempt in range(80):
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        last_start_error = None
                        break
            except Exception as exc:
                last_start_error = exc
                time.sleep(0.1)
        if last_start_error is not None:
            raise RuntimeError(f"Editor server did not start: {last_start_error}")
        # Run the workspace as a dedicated Edge app window. This avoids pywebview
        # renderer failures while keeping logins in a private application profile.
        edge_candidates = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        edge_exe = next((item for item in edge_candidates if item.is_file()), None)
        if edge_exe is None:
            raise RuntimeError("Không tìm thấy Microsoft Edge để mở TEAMSPIRIT-JP Workspace")
        app_profile = BROWSER_PROFILE.parent / "edge-app-profile"
        app_profile.mkdir(parents=True, exist_ok=True)
        launched_at = time.monotonic()
        app_url = f"{url}?session={int(time.time())}"
        LAST_APP_HEARTBEAT = 0.0
        subprocess.Popen([
            str(edge_exe),
            f"--app={app_url}",
            f"--user-data-dir={app_profile}",
            "--start-maximized",
            "--no-first-run",
            "--disable-features=msEdgeSidebarV2",
        ])
        saw_heartbeat = False
        try:
            while True:
                now = time.monotonic()
                if LAST_APP_HEARTBEAT >= launched_at:
                    saw_heartbeat = True
                if saw_heartbeat and now - LAST_APP_HEARTBEAT > 15:
                    break
                time.sleep(1)
        finally:
            server.shutdown()
            server.server_close()
