import os
import json
import argparse
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration (Cấu hình) ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITEMAP_PATH = os.path.join(REPO_ROOT, 'sitemap.xml')
CACHE_PATH = os.path.join(REPO_ROOT, 'tools', '.sitemap-cache.txt')
SCOPES = ["https://www.googleapis.com/auth/indexing"]

def load_sitemap_urls(sitemap_file):
    """Load URLs from sitemap.xml"""
    if not os.path.exists(sitemap_file):
        print(f"Sitemap file not found at {sitemap_file}")
        return set()
    
    tree = ET.parse(sitemap_file)
    root = tree.getroot()
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = set()
    for url in root.findall('ns:url/ns:loc', namespace):
        if url.text:
            urls.add(url.text)
    return urls

def load_cache(cache_file):
    """Load previously submitted URLs from cache"""
    if not os.path.exists(cache_file):
        return set()
    with open(cache_file, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_cache(cache_file, urls):
    """Save submitted URLs to cache"""
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        for url in sorted(urls):
            f.write(f"{url}\n")

def submit_to_google(urls_to_update, urls_to_delete, credentials_json, dry_run=False):
    """Gửi URLs lên Google Indexing API"""
    if not urls_to_update and not urls_to_delete:
        print("No new/updated or deleted URLs to submit.")
        return True
        
    try:
        # Load credentials
        creds_dict = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('indexing', 'v3', credentials=creds)
        
        submitted_count = 0
        max_quota = 200 # Google's daily quota limit for indexing API
        
        # Submit UPDATES
        for url in urls_to_update:
            if submitted_count >= max_quota:
                print("Reached daily quota limit of 200 requests.")
                break
                
            print(f"[{'DRY-RUN' if dry_run else 'API'}] Submitting URL_UPDATED: {url}")
            if not dry_run:
                try:
                    response = service.urlNotifications().publish(
                        body={
                            "url": url,
                            "type": "URL_UPDATED"
                        }
                    ).execute()
                    print(f"  Success: {response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('type')}")
                except HttpError as e:
                     print(f"  Error submitting {url}: {e}")
            submitted_count += 1
            
        # Submit DELETIONS
        for url in urls_to_delete:
            if submitted_count >= max_quota:
                print("Reached daily quota limit of 200 requests.")
                break
                
            print(f"[{'DRY-RUN' if dry_run else 'API'}] Submitting URL_DELETED: {url}")
            if not dry_run:
                try:
                    response = service.urlNotifications().publish(
                        body={
                            "url": url,
                            "type": "URL_DELETED"
                        }
                    ).execute()
                    print(f"  Success: {response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('type')}")
                except HttpError as e:
                     print(f"  Error submitting {url}: {e}")
            submitted_count += 1
            
        return True
    except Exception as e:
        print(f"Failed to initialize Google Indexing API: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Google Indexing API Submitter")
    parser.add_argument('--dry-run', action='store_true', help="Preview submissions without calling API")
    args = parser.parse_args()

    # Kiểm tra biến môi trường
    creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not creds_json:
        print("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set.")
        print("Skipping Google Indexing API submission.")
        return # Graceful exit (code 0)
        
    print("Starting Google Indexing API submission process...")
    
    current_urls = load_sitemap_urls(SITEMAP_PATH)
    cached_urls = load_cache(CACHE_PATH)
    
    urls_to_update = current_urls - cached_urls
    urls_to_delete = cached_urls - current_urls
    
    print(f"Found {len(current_urls)} URLs in sitemap.")
    print(f"Found {len(cached_urls)} URLs in cache.")
    print(f"URLs to Update/Add: {len(urls_to_update)}")
    print(f"URLs to Delete: {len(urls_to_delete)}")
    
    success = submit_to_google(urls_to_update, urls_to_delete, creds_json, dry_run=args.dry_run)
    
    if success and not args.dry_run:
        print("Updating cache file...")
        save_cache(CACHE_PATH, current_urls)
        
    print("Process complete.")

if __name__ == "__main__":
    main()
