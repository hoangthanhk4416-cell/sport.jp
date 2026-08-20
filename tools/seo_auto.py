#!/usr/bin/env python3
"""Automatic SEO maintenance for teamspiritsport.jp.

- Finds public index.html pages in the repository.
- Rebuilds sitemap.xml automatically.
- Audits title, meta description, canonical, H1 and internal links.
- Writes seo-report.json for quick review.

Uses Python standard library only.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://teamspiritsport.jp/"
EXCLUDED_TOP_LEVEL = {
    ".git",
    ".github",
    "admin",
    "admin_backend",
    "assets",
    "integrations",
    "tools",
}
EXCLUDED_FILES = {"404.html"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.h1_count = 0
        self.links: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.description = attrs.get("content", "").strip()
            elif name == "robots":
                self.robots = attrs.get("content", "").strip().lower()
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a":
            href = attrs.get("href", "").strip()
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def is_public_html(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.name in EXCLUDED_FILES:
        return False
    if rel.name.startswith("google") and rel.suffix == ".html":
        return False
    if rel.parts and rel.parts[0] in EXCLUDED_TOP_LEVEL:
        return False
    return rel.name == "index.html"


def page_url(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel == Path("index.html"):
        return BASE_URL
    folder = rel.parent.as_posix().strip("/")
    return urljoin(BASE_URL, folder + "/")


def git_lastmod(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        value = result.stdout.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return value
    except OSError:
        pass
    return date.today().isoformat()


def normalize_internal_target(source_url: str, href: str) -> str | None:
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urljoin(source_url, href)
    parsed = urlparse(absolute)
    if parsed.netloc and parsed.netloc != urlparse(BASE_URL).netloc:
        return None
    path = parsed.path or "/"
    if path.endswith("/"):
        return path
    if path.endswith(".html"):
        return path
    suffix = Path(path).suffix.lower()
    if suffix:
        return None
    return path + "/"


def build_pages() -> list[Path]:
    return sorted(p for p in ROOT.rglob("index.html") if is_public_html(p))


def write_sitemap(pages: list[Path]) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in pages:
        lines.append(
            f"  <url><loc>{page_url(path)}</loc><lastmod>{git_lastmod(path)}</lastmod></url>"
        )
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit(pages: list[Path]) -> dict:
    known_paths = {urlparse(page_url(p)).path for p in pages}
    issues = []
    page_results = []

    for path in pages:
        url = page_url(path)
        parser = PageParser()
        try:
            parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            issues.append({"url": url, "type": "parse_error", "detail": str(exc)})
            continue

        title = " ".join(parser.title.split())
        description = " ".join(parser.description.split())
        page_issues = []

        if not title:
            page_issues.append("missing_title")
        elif len(title) > 65:
            page_issues.append("title_too_long")
        if not description:
            page_issues.append("missing_meta_description")
        elif len(description) > 170:
            page_issues.append("meta_description_too_long")
        if not parser.canonical:
            page_issues.append("missing_canonical")
        elif urljoin(url, parser.canonical).rstrip("/") != url.rstrip("/"):
            page_issues.append("canonical_mismatch")
        if parser.h1_count == 0:
            page_issues.append("missing_h1")
        elif parser.h1_count > 1:
            page_issues.append("multiple_h1")
        if "noindex" in parser.robots:
            page_issues.append("noindex")

        broken = []
        for href in parser.links:
            target = normalize_internal_target(url, href)
            if target and target not in known_paths:
                if not target.startswith(("/admin/", "/assets/", "/integrations/")):
                    broken.append(href)
        if broken:
            page_issues.append("broken_internal_links")

        for item in page_issues:
            issues.append({"url": url, "type": item})

        page_results.append(
            {
                "url": url,
                "title": title,
                "description_length": len(description),
                "canonical": parser.canonical,
                "h1_count": parser.h1_count,
                "broken_internal_links": sorted(set(broken)),
                "issues": page_issues,
            }
        )

    return {
        "site": BASE_URL,
        "generated": date.today().isoformat(),
        "pages": len(pages),
        "issue_count": len(issues),
        "issues": issues,
        "details": page_results,
    }


def main() -> None:
    pages = build_pages()
    write_sitemap(pages)
    report = audit(pages)
    (ROOT / "seo-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"SEO auto: {len(pages)} pages, {report['issue_count']} issues")
    print("Updated sitemap.xml and seo-report.json")


if __name__ == "__main__":
    main()

# Workflow trigger marker: initial installation complete.
