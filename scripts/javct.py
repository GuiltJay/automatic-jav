from __future__ import annotations

import cloudscraper
import csv
import json
import os
import time
import random
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

# =========================
# CONFIGURATION
# =========================

BASE_URL = "https://javct.net"
DELAY_MIN = 1.0
DELAY_MAX = 2.5
MAX_RETRIES = 5
RETRY_DELAY = 5.0
MAX_CATEGORIES = 5  # "fetch from many categories" -> we'll fetch top 5

RAW_DIR = Path("results/raw_javct")
MASTER_CSV = Path("results/processed/javct.csv")
MODELS_CSV = Path("results/processed/javct_models.csv")

os.chdir(Path(__file__).resolve().parent.parent)

# =========================
# DATA MODELS
# =========================

@dataclass
class JavctVideo:
    code: str
    title: str
    image_url: str
    page_url: str
    views: str
    date_scraped: str

@dataclass
class JavctModel:
    name: str
    image_url: str
    page_url: str
    views: str
    date_scraped: str

VIDEO_FIELDS = ["code", "title", "image_url", "page_url", "views", "date_scraped"]
MODEL_FIELDS = ["name", "image_url", "page_url", "views", "date_scraped"]

# =========================
# SCRAPER CORE
# =========================

scraper = cloudscraper.create_scraper()

def get_with_retry(url: str, retries: int = MAX_RETRIES) -> Optional[str]:
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
        except Exception as e:
            print(f"  -> Error: {e}. Retrying...")
        
        if attempt < retries:
            time.sleep(RETRY_DELAY * attempt)
        else:
            print(f"  -> Failed after {retries} attempts: {url}")
            return None
    return None

def parse_videos(html: str) -> List[JavctVideo]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for card in soup.select("div.card"):
        try:
            # Code is usually in span.card__category
            cat_el = card.select_one("span.card__category a")
            code = cat_el.get_text(strip=True) if cat_el else ""
            if not code:
                continue

            title_el = card.select_one("h3.card__title a")
            title = title_el.get_text(strip=True) if title_el else ""
            
            # The play button href holds the url
            play_el = card.select_one("a.card__play")
            page_url = urljoin(BASE_URL, str(play_el.get("href", ""))) if play_el else ""
            
            img_el = card.select_one("img.lazy")
            image_url = ""
            if img_el:
                image_url = str(img_el.get("data-src", img_el.get("src", "")))

            rate_el = card.select_one("span.card__rate")
            views = rate_el.get_text(strip=True) if rate_el else ""

            items.append(JavctVideo(
                code=code,
                title=title,
                image_url=image_url,
                page_url=page_url,
                views=views,
                date_scraped=today
            ))
        except Exception as e:
            print(f"[video parse error] {e}")
            continue

    return items

def parse_models(html: str) -> List[JavctModel]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for card in soup.select("div.card"):
        try:
            title_el = card.select_one("h3.card__title a")
            if not title_el:
                continue
                
            name = title_el.get_text(strip=True)
            page_url = urljoin(BASE_URL, str(title_el.get("href", "")))
            
            img_el = card.select_one("img.lazy")
            image_url = ""
            if img_el:
                image_url = str(img_el.get("data-src", img_el.get("src", "")))

            rate_el = card.select_one("span.card__rate")
            views = rate_el.get_text(strip=True) if rate_el else ""

            items.append(JavctModel(
                name=name,
                image_url=image_url,
                page_url=page_url,
                views=views,
                date_scraped=today
            ))
        except Exception as e:
            print(f"[model parse error] {e}")
            continue

    return items

def parse_categories(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    # Both .card__title a and a.category might hold category links
    for a in soup.select(".card__title a"):
        href = str(a.get("href", ""))
        if "/category/" in href:
            urls.append(urljoin(BASE_URL, href))
            
    # If not found, try the direct list
    if not urls:
        for a in soup.select("a"):
            href = str(a.get("href", ""))
            if "/category/" in href:
                urls.append(urljoin(BASE_URL, href))

    # deduplicate
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
            
    return unique

def save_items(folder: str, filename: str, items: list, is_model: bool = False):
    if not items:
        return
        
    out_dir = RAW_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize
    safe_name = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    csv_path = out_dir / f"{safe_name}.csv"
    
    fields = MODEL_FIELDS if is_model else VIDEO_FIELDS
    
    # Deduplicate within batch
    seen = set()
    unique = []
    for it in items:
        key = getattr(it, "name" if is_model else "code").lower()
        if key not in seen:
            seen.add(key)
            unique.append(it)
            
    rows = [asdict(it) for it in unique]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"[✓] Saved {len(rows)} items to {folder}/{safe_name}.csv")

# =========================
# TASKS
# =========================

def scrape_videos():
    endpoints = [
        ("amateur", "/amateur"),
        ("amateur_new", "/amateur?sort=new-releases"),
        ("uncensored_most_viewed", "/uncensored?sort=most-viewed"),
        ("uncensored", "/uncensored"),
    ]
    
    for name, path in endpoints:
        url = urljoin(BASE_URL, path)
        html = get_with_retry(url)
        if html:
            items = parse_videos(html)
            save_items("videos", name, items)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            
def scrape_categories_videos():
    url = urljoin(BASE_URL, "/categories")
    html = get_with_retry(url)
    if not html:
        return
        
    cat_urls = parse_categories(html)[:MAX_CATEGORIES]
    print(f"[*] Found categories, will scrape top {len(cat_urls)}")
    
    for c_url in cat_urls:
        c_name = c_url.rstrip("/").split("/")[-1]
        c_html = get_with_retry(c_url)
        if c_html:
            items = parse_videos(c_html)
            save_items("categories", c_name, items)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

def scrape_models_page():
    url = urljoin(BASE_URL, "/models")
    html = get_with_retry(url)
    if html:
        items = parse_models(html)
        save_items("models", "models_index", items, is_model=True)

# =========================
# MERGE LOGIC
# =========================

def merge_csvs():
    """Merge all video and model CSVs into master files."""
    if not RAW_DIR.exists():
        return
        
    # Videos
    v_seen = set()
    v_rows = []
    for f in RAW_DIR.rglob("*.csv"):
        if "models" in f.parts:
            continue
        with f.open(newline="", encoding="utf-8") as file:
            for r in csv.DictReader(file):
                code = r.get("code", "").strip().lower()
                if not code or code in v_seen:
                    continue
                v_seen.add(code)
                v_rows.append(r)
                
    if v_rows:
        MASTER_CSV.parent.mkdir(parents=True, exist_ok=True)
        with MASTER_CSV.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=VIDEO_FIELDS)
            writer.writeheader()
            writer.writerows(v_rows)
        print(f"[✓] Master Video CSV: {MASTER_CSV} ({len(v_rows)} rows)")
        
    # Models
    m_seen = set()
    m_rows = []
    for f in (RAW_DIR / "models").glob("*.csv"):
        with f.open(newline="", encoding="utf-8") as file:
            for r in csv.DictReader(file):
                name = r.get("name", "").strip().lower()
                if not name or name in m_seen:
                    continue
                m_seen.add(name)
                m_rows.append(r)
                
    if m_rows:
        MODELS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with MODELS_CSV.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=MODEL_FIELDS)
            writer.writeheader()
            writer.writerows(m_rows)
        print(f"[✓] Master Model CSV: {MODELS_CSV} ({len(m_rows)} rows)")

# =========================
# MAIN
# =========================

def main():
    print("--- Scraping Video Endpoints ---")
    scrape_videos()
    print("\n--- Scraping Categories ---")
    scrape_categories_videos()
    print("\n--- Scraping Models ---")
    scrape_models_page()
    print("\n--- Merging Data ---")
    merge_csvs()

if __name__ == "__main__":
    main()
