#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import csv
import time
import random
import os
from datetime import datetime

BASE_URL = "https://jav.guru/page/{}/"
PAGES_TO_FETCH = 20  # adjust as needed

pattern = re.compile(r"^https?://jav\.guru/\d+/.+")
results = set()

# Ensure results folder exists
OUT_DIR = "results/raw"
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )

    page = context.new_page()

    # Warm-up (important for Cloudflare)
    print("🔥 Warming up homepage")
    page.goto("https://jav.guru/", wait_until="networkidle")
    time.sleep(3)

    for page_num in range(1, PAGES_TO_FETCH + 1):
        url = BASE_URL.format(page_num)
        print(f"📥 Fetching: {url}")

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            html = page.content()
        except Exception as e:
            print(f"❌ Failed {url}: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if pattern.match(href):
                img = a_tag.find("img")
                if img and img.get("src"):
                    results.add((href, img["src"]))

        print(f"✅ Page {page_num} done, total links: {len(results)}")

        time.sleep(random.uniform(3, 6))  # human-like delay

    browser.close()

# Filename with current date & time
today = datetime.now().strftime("%Y-%m-%d_%H%M%S")
filename = f"jav_links_{today}.csv"
filepath = os.path.join(OUT_DIR, filename)

# Save to CSV
with open(filepath, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["page_url", "image_url"])
    for row in sorted(results):
        writer.writerow(row)

print(f"\n🎉 Saved {len(results)} unique entries to {filepath}")
