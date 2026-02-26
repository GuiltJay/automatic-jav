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
from typing import List
from urllib.parse import urljoin

# =========================
# CONFIGURATION
# =========================

BASE_URL = "https://onejav.com"
DAYS_TO_SCRAPE = 7          # scrape last N days of listings
DELAY_MIN = 1.0             # polite delay between requests
DELAY_MAX = 2.5

RAW_DIR = "results/raw_onejav"
MASTER_CSV = "results/processed/onejav.csv"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

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


# =========================
# PARSER
# =========================

def parse_listing_page(html: str, page_date: str) -> List[TorrentItem]:
    """Parse a date listing page and extract all torrent items."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for card in soup.select("div.card.mb-3"):
        try:
            # Code
            title_el = card.select_one("h5.title a")
            if not title_el:
                continue
            code = title_el.get_text(strip=True)
            page_url = urljoin(BASE_URL, title_el.get("href", ""))

            # Size
            size_el = card.select_one("h5.title span.is-size-6")
            size = size_el.get_text(strip=True) if size_el else ""

            # Image
            img_el = card.select_one("img.image")
            image_url = img_el.get("src", "") if img_el else ""

            # Date from card (fallback to page_date)
            date_el = card.select_one("p.subtitle a")
            date_str = page_date
            if date_el:
                href = date_el.get("href", "")
                m = re.search(r"/(\d{4})/(\d{2})/(\d{2})", href)
                if m:
                    date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            # Tags
            tag_els = card.select("div.tags a.tag")
            tags = [t.get_text(strip=True) for t in tag_els]

            # Description / title text
            desc_el = card.select_one("p.level.has-text-grey-dark")
            title_text = desc_el.get_text(strip=True) if desc_el else ""

            # Actresses
            actress_els = card.select("div.panel a.panel-block")
            actresses = [a.get_text(strip=True) for a in actress_els]

            # Torrent download URL
            dl_el = card.select_one("a.button[href*='/download/']")
            torrent_url = ""
            if dl_el:
                torrent_url = urljoin(BASE_URL, dl_el.get("href", ""))

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


# =========================
# DATE URL GENERATION
# =========================

def get_date_urls(days: int) -> List[tuple[str, str]]:
    """Generate date-based listing URLs for the last N days."""
    urls = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        url = f"{BASE_URL}/{d.strftime('%Y/%m/%d')}"
        urls.append((url, date_str))
    return urls


# =========================
# MAIN SCRAPER
# =========================

def scrape_all() -> List[TorrentItem]:
    scraper = cloudscraper.create_scraper()

    date_urls = get_date_urls(DAYS_TO_SCRAPE)
    # Also add /new page
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_urls = [(f"{BASE_URL}/new", today_str)] + date_urls

    print(f"[onejav] Scraping {len(all_urls)} pages ({DAYS_TO_SCRAPE} days + /new)")

    all_items: List[TorrentItem] = []
    seen_codes: set[str] = set()

    for url, date_str in all_urls:
        try:
            r = scraper.get(url)
            if r.status_code != 200:
                print(f"[{r.status_code}] {url}")
                continue

            items = parse_listing_page(r.text, date_str)
            new_count = 0
            for item in items:
                key = item.code.lower()
                if key not in seen_codes:
                    seen_codes.add(key)
                    all_items.append(item)
                    new_count += 1

            print(f"[onejav] {url} -> {len(items)} items ({new_count} new)")

        except Exception as e:
            print(f"[error] {url}: {e}")

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    print(f"[onejav] Total unique items: {len(all_items)}")
    return all_items


# =========================
# CSV / JSON OUTPUT
# =========================

FIELDNAMES = [
    "code", "title", "size", "image_url", "torrent_url",
    "tags", "actresses", "date", "page_url",
]


def save_daily(items: List[TorrentItem]):
    """Save today's scrape as raw CSV + JSON."""
    os.makedirs(RAW_DIR, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    csv_path = os.path.join(RAW_DIR, f"onejav_{today}.csv")
    json_path = os.path.join(RAW_DIR, f"onejav_{today}.json")

    rows = [asdict(it) for it in items]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[✓] Daily files: {csv_path} ({len(rows)} rows), {json_path}")


def merge_daily_csvs():
    """Merge all raw CSVs into master CSV, deduplicated by code."""
    seen: set[str] = set()
    rows: list[dict] = []

    if not os.path.isdir(RAW_DIR):
        return

    for file in sorted(os.listdir(RAW_DIR)):
        if not file.endswith(".csv"):
            continue
        with open(os.path.join(RAW_DIR, file), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                code = r.get("code", "").strip().lower()
                if not code or code in seen:
                    continue
                seen.add(code)
                rows.append(r)

    os.makedirs(os.path.dirname(MASTER_CSV), exist_ok=True)

    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Master CSV: {MASTER_CSV} ({len(rows)} rows)")


# =========================
# MAIN
# =========================

def main():
    items = scrape_all()
    if items:
        save_daily(items)
    merge_daily_csvs()


if __name__ == "__main__":
    main()
