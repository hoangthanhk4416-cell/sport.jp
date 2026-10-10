import os
import re
import json
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup

# --- Configuration (Cấu hình) ---
BASE_URL = "https://teamspiritsport.jp"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EXCLUDED_DIRS = ['admin', 'admin_backend', 'tests', 'tools', '.git', '.github']
EXCLUDED_FILES_PATTERN = re.compile(r'^(404\.html|google.*\.html)$')

# Priorities for different page types
PRIORITIES = {
    'index.html': '1.0',
    'product': '0.8',
    'blog': '0.7',
    'collection': '0.7',
    'default': '0.5'
}

def get_file_mod_time(filepath):
    """Lấy thời gian sửa đổi của file (Git commit date or filesystem mtime)"""
    try:
        # Try to get the last commit date for the file (YYYY-MM-DD format)
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%cs', '--', filepath],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return result.stdout.strip()  # Returns YYYY-MM-DD
    except Exception:
        pass
    
    # Fallback to file system modification time
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')

def scan_html_files():
    """Quét tất cả các file HTML trong repository"""
    html_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]
        
        for file in files:
            if file.endswith('.html') and not EXCLUDED_FILES_PATTERN.match(file):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, REPO_ROOT)
                html_files.append((filepath, rel_path.replace('\\', '/')))
    return html_files

def get_url_and_priority(rel_path):
    """Tính toán URL và độ ưu tiên (Priority)"""
    # Convert directory/index.html → directory/ (trailing slash format)
    if rel_path == 'index.html':
        url = BASE_URL + "/"
        priority = PRIORITIES['index.html']
    elif rel_path.endswith('/index.html'):
        # about/index.html → /about/
        url = f"{BASE_URL}/{rel_path[:-len('index.html')]}"
        if 'products/' in rel_path:
            priority = PRIORITIES['product']
        elif 'blog/' in rel_path:
            priority = PRIORITIES['blog']
        elif 'collections/' in rel_path:
            priority = PRIORITIES['collection']
        else:
            priority = PRIORITIES['default']
    else:
        # other.html → /other.html (keep as-is)
        url = f"{BASE_URL}/{rel_path}"
        if 'products/' in rel_path:
            priority = PRIORITIES['product']
        elif 'blog/' in rel_path:
            priority = PRIORITIES['blog']
        elif 'collections/' in rel_path:
            priority = PRIORITIES['collection']
        else:
            priority = PRIORITIES['default']
        
    return url, priority

def generate_sitemap(html_files):
    """Tạo sitemap.xml"""
    sitemap_path = os.path.join(REPO_ROOT, 'sitemap.xml')
    
    urls = []
    for filepath, rel_path in html_files:
        url, priority = get_url_and_priority(rel_path)
        lastmod = get_file_mod_time(filepath)
        urls.append({
            'loc': url,
            'lastmod': lastmod,
            'changefreq': 'weekly',
            'priority': priority
        })
        
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for item in urls:
            f.write('  <url>\n')
            f.write(f'    <loc>{item["loc"]}</loc>\n')
            f.write(f'    <lastmod>{item["lastmod"]}</lastmod>\n')
            f.write(f'    <changefreq>{item["changefreq"]}</changefreq>\n')
            f.write(f'    <priority>{item["priority"]}</priority>\n')
            f.write('  </url>\n')
        f.write('</urlset>\n')
        
    print(f"Generated sitemap.xml with {len(urls)} URLs.")
    return urls

def run_seo_audit(html_files):
    """Chạy SEO Audit (Kiểm tra SEO)"""
    report = {
        "site": BASE_URL,
        "generated": datetime.utcnow().isoformat() + "Z",
        "pages": len(html_files),
        "issue_count": 0,
        "issues": []
    }
    
    valid_paths = [rel_path for _, rel_path in html_files]
    
    for filepath, rel_path in html_files:
        url, _ = get_url_and_priority(rel_path)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'lxml')
        
        # Check noindex
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta and 'noindex' in robots_meta.get('content', '').lower():
            report["issues"].append({"url": url, "type": "noindex", "detail": "Page has noindex meta tag"})
            continue # Skip other checks if noindex
            
        # Title check
        title_tag = soup.find('title')
        if not title_tag or not title_tag.text.strip():
            report["issues"].append({"url": url, "type": "missing_title", "detail": "Missing or empty <title> tag"})
            
        # Meta description check
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if not desc_meta or not desc_meta.get('content', '').strip():
            report["issues"].append({"url": url, "type": "missing_meta_description", "detail": "Missing or empty meta description"})
        else:
            desc_len = len(desc_meta.get('content', '').strip())
            if desc_len < 50:
                report["issues"].append({"url": url, "type": "short_meta_description", "detail": f"Meta description too short ({desc_len} chars)"})
            elif desc_len > 160:
                report["issues"].append({"url": url, "type": "long_meta_description", "detail": f"Meta description too long ({desc_len} chars)"})
                
        # H1 check
        h1_tags = soup.find_all('h1')
        if len(h1_tags) == 0:
            report["issues"].append({"url": url, "type": "missing_h1", "detail": "Missing <h1> tag"})
        elif len(h1_tags) > 1:
            report["issues"].append({"url": url, "type": "multiple_h1", "detail": f"Multiple <h1> tags found ({len(h1_tags)})"})
            
        # Canonical link check
        canonical_link = soup.find('link', rel='canonical')
        if not canonical_link:
            report["issues"].append({"url": url, "type": "missing_canonical", "detail": "Missing canonical link"})
        elif canonical_link.get('href') != url:
            report["issues"].append({"url": url, "type": "canonical_mismatch", "detail": f"Canonical URL ({canonical_link.get('href')}) does not match expected URL ({url})"})
            
        # Open Graph tags check
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')
        if not (og_title and og_desc and og_image):
             report["issues"].append({"url": url, "type": "missing_og_tags", "detail": "Missing one or more Open Graph tags (og:title, og:description, og:image)"})
             
        # Image alt text check
        images = soup.find_all('img')
        for img in images:
            if not img.get('alt'):
                report["issues"].append({"url": url, "type": "missing_alt_text", "detail": f"Image missing alt attribute: {img.get('src', 'unknown')}"})
                
        # Internal links check
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            if href.startswith('http') or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            # Simple relative path check
            clean_href = href.split('#')[0].split('?')[0].lstrip('/')
            if clean_href == '':
                clean_href = 'index.html'
                
            if clean_href.endswith('.html') and clean_href not in valid_paths:
                 report["issues"].append({"url": url, "type": "broken_internal_link", "detail": f"Broken internal link to: {href}"})
                 
    report["issue_count"] = len(report["issues"])
    
    report_path = os.path.join(REPO_ROOT, 'seo-report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(f"\nSEO Audit Complete. Found {report['issue_count']} issues across {report['pages']} pages.")
    print("Top issues:")
    
    # Print summary
    issue_types = {}
    for issue in report["issues"]:
        issue_types[issue["type"]] = issue_types.get(issue["type"], 0) + 1
        
    for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
        print(f" - {issue_type}: {count}")
        
if __name__ == "__main__":
    print("Starting SEO Automation...")
    files = scan_html_files()
    print(f"Found {len(files)} HTML files to process.")
    
    generate_sitemap(files)
    run_seo_audit(files)
