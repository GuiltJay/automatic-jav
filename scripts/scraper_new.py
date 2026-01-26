#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import csv
import time
import random
import os
from datetime import datetime

# ---------------- CONFIG ----------------

BASE_URL = "https://jav.guru/page/{}/"
PAGES_TO_FETCH = 20

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

pattern = re.compile(r"^https?://jav\.guru/\d+/.+")
results = set()

OUT_DIR = "results/raw"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------- MAIN ----------------

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800},
    )

    page = context.new_page()

    # 🔥 Warm up homepage (Cloudflare trust)
    print("🔥 Warming up homepage")
    page.goto("https://jav.guru/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    for page_num in range(1, PAGES_TO_FETCH + 1):
        url = BASE_URL.format(page_num)
        print(f"📥 Fetching: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # wait for real content
            page.wait_for_selector(
                "a[href^='https://jav.guru/']",
                timeout=30000
            )

            # trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            html = page.content()

        except Exception as e:
            print(f"❌ Failed {url}: {e}")
            continue

        # -------- OLD LOGIC (UNCHANGED) --------

        soup = BeautifulSoup(html, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if pattern.match(href):
                img = a_tag.find("img")
                if img:
                    img_url = img.get("data-src") or img.get("src")
                    if img_url:
                        results.add((href, img_url))

        print(f"✅ Page {page_num} done, total links: {len(results)}")

        time.sleep(random.uniform(3, 6))  # human delay

    browser.close()

# ---------------- SAVE CSV ----------------

today = datetime.now().strftime("%Y-%m-%d_%H%M%S")
filename = f"jav_links_{today}.csv"
filepath = os.path.join(OUT_DIR, filename)

with open(filepath, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["page_url", "image_url"])
    for row in sorted(results):
        writer.writerow(row)

print(f"\n🎉 Saved {len(results)} unique entries to {filepath}")
