from __future__ import annotations

import cloudscraper
import csv
import json
import os
import re
import time
import random
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, unquote

# =========================
# CONFIGURATION
# =========================

BASE_URL = "https://onejav.com"
DAYS_TO_SCRAPE = 20         # fetch for at least 20 days
DELAY_MIN = 1.0             # polite delay between requests
DELAY_MAX = 2.5
MAX_RETRIES = 5             # retry retry retryretry
RETRY_DELAY = 5.0           # wait seconds before retry

# Directories
RAW_DIR = Path("results/raw_onejav")
MASTER_CSV = Path("results/processed/onejav.csv")

# Ensure working directory is the project root
os.chdir(Path(__file__).resolve().parent.parent)

# Configurable endpoints
TAGS_TO_SCRAPE = ["JavPlayer", "Cuckold", "Creampie", "Amateur", "Documentary"]
TOP_NEW_ACTRESSES_LIMIT = 10

# =========================
# DATA MODEL
# =========================

@dataclass
class TorrentItem:
    code: str
    title: str
    size: str
    image_url: str
    torrent_url: str
    tags: str           # comma-separated
    actresses: str      # comma-separated
    date: str           # YYYY-MM-DD
    page_url: str


FIELDNAMES = [
    "code", "title", "size", "image_url", "torrent_url",
    "tags", "actresses", "date", "page_url",
]

# =========================
# CLOUDSCRAPER W/ RETRY
# =========================

scraper = cloudscraper.create_scraper()

def get_with_retry(url: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """Robust fetch with exponential-ish backoff retry logic."""
    for attempt in range(1, retries + 1):
        try:
            print(f"[get] {url} (Attempt {attempt}/{retries})")
            r = scraper.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
            elif r.status_code in [403, 429, 500, 502, 503, 504]:
                print(f"  -> HTTP {r.status_code}. Retrying...")
            elif r.status_code == 404:
                print(f"  -> HTTP 404 Not Found (skipping).")
                return None
            else:
                print(f"  -> HTTP {r.status_code}. Retrying...")
        except Exception as e:
            print(f"  -> Error: {e}. Retrying...")
        
        if attempt < retries:
            time.sleep(RETRY_DELAY * attempt)
        else:
            print(f"  -> Failed after {retries} attempts: {url}")
            return None
    return None

# =========================
# PARSER
# =========================

def parse_listing_page(html: str, fallback_date: str) -> List[TorrentItem]:
    """Parse a OneJAV page (date, tag, actress, popular, new, torrent) and extract cards."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for card in soup.select("div.card.mb-3"):
        try:
            title_el = card.select_one("h5.title a")
            if not title_el:
                continue
            code = title_el.get_text(strip=True)
            page_url = urljoin(BASE_URL, str(title_el.get("href", "")))

            size_el = card.select_one("h5.title span.is-size-6")
            size = size_el.get_text(strip=True) if size_el else ""

            img_el = card.select_one("img.image")
            image_url = str(img_el.get("src", "")) if img_el else ""

            # Extract date from link like "/2026/02/26"
            date_el = card.select_one("p.subtitle a")
            date_str = fallback_date
            if date_el:
                href = str(date_el.get("href", ""))
                m = re.search(r"/(\d{4})/(\d{2})/(\d{2})", href)
                if m:
                    date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            tag_els = card.select("div.tags a.tag")
            tags = [t.get_text(strip=True) for t in tag_els]

            desc_el = card.select_one("p.level.has-text-grey-dark")
            title_text = desc_el.get_text(strip=True) if desc_el else ""

            actress_els = card.select("div.panel a.panel-block")
            actresses = [a.get_text(strip=True) for a in actress_els]

            dl_el = card.select_one("a.button[href*='/download/']")
            torrent_url = ""
            if dl_el:
                torrent_url = urljoin(BASE_URL, str(dl_el.get("href", "")))

            items.append(TorrentItem(
                code=code,
                title=title_text,
                size=size,
                image_url=image_url,
                torrent_url=torrent_url,
                tags=", ".join(tags),
                actresses=", ".join(actresses),
                date=date_str,
                page_url=page_url,
            ))

        except Exception as e:
            print(f"[parse error] {e}")
            continue

    return items


def scrape_endpoint(url: str, fallback_date: str) -> List[TorrentItem]:
    """Fetch URL and extract TorrentItems. Includes polite delay."""
    html = get_with_retry(url)
    if not html:
        return []
    items = parse_listing_page(html, fallback_date)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    return items

# =========================
# STORAGE
# =========================

def save_to_folder(folder_name: str, file_name: str, items: List[TorrentItem]):
    """Save extracted items to specific subfolder inside results/raw_onejav/."""
    if not items:
        return
        
    out_dir = RAW_DIR / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize file_name to avoid directory traversal or bad chars
    safe_name = "".join([c for c in file_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    
    csv_path = out_dir / f"{safe_name}.csv"
    json_path = out_dir / f"{safe_name}.json"
    
    # Deduplicate items before saving (in case of dupes on the same page)
    seen = set()
    unique_items = []
    for it in items:
        k = it.code.lower()
        if k not in seen:
            seen.add(k)
            unique_items.append(it)
            
    rows = [asdict(it) for it in unique_items]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[✓] Saved {len(rows)} items to {folder_name}/{safe_name}")

# =========================
# SCRAPING ROUTINES
# =========================

def scrape_dates():
    """Scrape the last N days (default 20)."""
    print("\n--- Scraping Dates ---")
    today = datetime.now(timezone.utc).date()
    for i in range(DAYS_TO_SCRAPE):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        url = f"{BASE_URL}/{d.strftime('%Y/%m/%d')}"
        
        items = scrape_endpoint(url, fallback_date=date_str)
        save_to_folder("dates", date_str, items)

def scrape_lists():
    """Scrape /new and /popular/."""
    print("\n--- Scraping Lists ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    new_items = scrape_endpoint(f"{BASE_URL}/new", fallback_date=today_str)
    save_to_folder("lists", "new", new_items)
    
    popular_items = scrape_endpoint(f"{BASE_URL}/popular/", fallback_date=today_str)
    save_to_folder("lists", "popular", popular_items)

def scrape_tags():
    """Scrape predefined tags."""
    print("\n--- Scraping Tags ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    for tag in TAGS_TO_SCRAPE:
        url = f"{BASE_URL}/tag/{tag}"
        items = scrape_endpoint(url, fallback_date=today_str)
        save_to_folder("tags", tag, items)

def scrape_home_page():
    """Extract 'Actress of the Day' and 'Featured Torrents' from Home."""
    print("\n--- Scraping Home Page ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    html = get_with_retry(f"{BASE_URL}/")
    if not html:
        return
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract Actress of the Day
    actress_url = None
    actress_name = "ActressOfTheDay"
    for col in soup.select(".column"):
        if "Actress of the Day" in col.get_text():
            for a in col.select("a"):
                href = str(a.get("href", ""))
                if "/actress/" in href:
                    actress_url = urljoin(BASE_URL, href)
                    actress_name = a.get_text(strip=True)
                    break
            break
            
    if actress_url:
        print(f"[*] Found Actress of the Day: {actress_name} ({actress_url})")
        items = scrape_endpoint(actress_url, fallback_date=today_str)
        save_to_folder("home", f"actress_of_the_day_{unquote(actress_name)}", items)

    # Extract Featured Torrents
    featured_links = []
    for col in soup.select(".column"):
        if "Featured Torrents" in col.get_text():
            for a in col.select("a"):
                href = str(a.get("href", ""))
                if "/torrent/" in href:
                    featured_links.append(urljoin(BASE_URL, href))
            break
            
    if featured_links:
        print(f"[*] Found {len(featured_links)} Featured Torrents")
        featured_items = []
        for link in featured_links:
            items = scrape_endpoint(link, fallback_date=today_str)
            featured_items.extend(items)
        save_to_folder("home", "featured", featured_items)

def scrape_new_actresses():
    """Scrape top N actresses from the 'new releases' actress feed."""
    print("\n--- Scraping New Release Actresses ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/actress/?order=release"
    html = get_with_retry(url)
    if not html:
        return
        
    soup = BeautifulSoup(html, "html.parser")
    actress_urls = []
    
    # Grab actress links from columns
    for col in soup.select(".column"):
        for a in col.select("a"):
            href = str(a.get("href", ""))
            if "/actress/" in href:
                actress_urls.append((a.get_text(strip=True), urljoin(BASE_URL, href)))
                
    # Deduplicate and limit
    unique_actresses = []
    seen = set()
    for name, a_url in actress_urls:
        if name and name not in seen:
            seen.add(name)
            unique_actresses.append((name, a_url))
            
    top_actresses = unique_actresses[:TOP_NEW_ACTRESSES_LIMIT]
    print(f"[*] Scraping top {len(top_actresses)} new release actresses...")
    
    for name, a_url in top_actresses:
        items = scrape_endpoint(a_url, fallback_date=today_str)
        save_to_folder("actresses", f"{unquote(name)}", items)

# =========================
# MERGE LOGIC
# =========================

def merge_all_csvs():
    """Merge ALL .csv files recursively from results/raw_onejav/ -> onejav.csv"""
    print("\n--- Merging All Data ---")
    seen: set[str] = set()
    rows: list[dict] = []

    if not RAW_DIR.exists():
        return

    csv_files = list(RAW_DIR.rglob("*.csv"))
    print(f"[*] Found {len(csv_files)} CSV files to merge.")
    
    for file in sorted(csv_files, reverse=True):
        with file.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                code = r.get("code", "").strip().lower()
                if not code or code in seen:
                    continue
                seen.add(code)
                rows.append(r)

    MASTER_CSV.parent.mkdir(parents=True, exist_ok=True)

    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Master CSV: {MASTER_CSV} ({len(rows)} unique rows)")


# =========================
# MAIN
# =========================

def main():
    scrape_dates()
    scrape_lists()
    scrape_tags()
    scrape_home_page()
    scrape_new_actresses()
    
    merge_all_csvs()

if __name__ == "__main__":
    main()
