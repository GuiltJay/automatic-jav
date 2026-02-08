from __future__ import annotations

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import asyncio
import re
import sys
import os
import csv
import json
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# =========================
# CONFIGURATION
# =========================

CATEGORIES = [
    "https://missav123.com/dm291/en/today-hot/",
    # add more categories if needed
]

MAX_PAGES = 30              # pagination depth per category
PAGE_CONCURRENCY = 6        # concurrent listing pages
POST_CONCURRENCY = 12       # concurrent post pages

RAW_DIR = "results/raw_missav"
MASTER_CSV = "results/processed/missav.csv"

# =========================
# Optional engines
# =========================

try:
    from crawl4ai import AsyncWebCrawler  # type: ignore
    HAVE_CRAWL4AI = True
except Exception:
    HAVE_CRAWL4AI = False

try:
    import aiohttp  # type: ignore
    HAVE_AIOHTTP = True
except Exception:
    HAVE_AIOHTTP = False

# =========================
# Decoder utilities
# =========================

def unquote_js_string(s: str) -> str:
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        s = s[1:-1]
    return s.encode("utf-8").decode("unicode_escape")


def int_to_base(n: int, base: int) -> str:
    if n == 0:
        return "0"
    out = []
    while n:
        d = n % base
        out.append(str(d) if d < 10 else chr(ord("a") + d - 10))
        n //= base
    return "".join(reversed(out))


def decode_packed_eval(payload: str) -> Optional[str]:
    start = payload.find("eval(function(p,a,c,k,e,d)")
    if start == -1:
        return None

    chunk = payload[start:start + 20000]
    idx = chunk.find("}(")
    if idx == -1:
        return None

    args = chunk[idx + 2:]
    depth, buf = 1, []

    for ch in args:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0:
            break
        buf.append(ch)

    parts, cur = [], []
    sq = dq = esc = False
    pd = 0

    for ch in "".join(buf):
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            cur.append(ch)
            esc = True
            continue
        if ch == "'" and not dq:
            sq = not sq
        elif ch == '"' and not sq:
            dq = not dq
        elif ch == "(" and not sq and not dq:
            pd += 1
        elif ch == ")" and not sq and not dq:
            pd -= 1
        elif ch == "," and not sq and not dq and pd == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)

    if cur:
        parts.append("".join(cur).strip())

    if len(parts) < 4:
        return None

    p = unquote_js_string(parts[0])
    a, c = int(parts[1]), int(parts[2])
    k = unquote_js_string(parts[3].split(".split")[0]).split("|")

    for n in range(c - 1, -1, -1):
        key = int_to_base(n, a)
        val = k[n] if n < len(k) and k[n] else key
        p = re.sub(rf"\b{re.escape(key)}\b", val, p)

    return p


def extract_playlist_urls(text: str) -> List[str]:
    patterns = [
        r"https?://[^\s\"']+\.m3u8(?:\?[^\s\"']+)?",
        r"https?://[^\s\"']+/playlist(?:\.\w+)?(?:\?[^\s\"']+)?",
    ]
    urls = set()
    for pat in patterns:
        urls.update(re.findall(pat, text))
    return sorted(urls)

# =========================
# Fetching layer
# =========================

@dataclass
class Fetcher:
    session: Optional["aiohttp.ClientSession"] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url) as r:
                return await r.text(errors="ignore") if r.status == 200 else None
        except Exception:
            return None

# =========================
# Parsing helpers
# =========================

def extract_video_code(url: str) -> Optional[str]:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return slug.lower() if re.fullmatch(r"[a-z0-9]+-\d+", slug, re.I) else None


def infer_quality(url: str) -> str:
    if "1080" in url:
        return "1080p"
    if "720" in url:
        return "720p"
    if "480" in url:
        return "480p"
    return "playlist"


def infer_source(url: str) -> str:
    return urlparse(url).netloc.lower()

# =========================
# Workers
# =========================

async def process_post(url: str, fetcher: Fetcher, sem: asyncio.Semaphore):
    async with sem:
        html = await fetcher.fetch(url)
        if not html:
            return None
        decoded = decode_packed_eval(html) or html
        return url, extract_playlist_urls(decoded)

# =========================
# Pagination + categories
# =========================

async def collect_posts_for_category(
    start_url: str,
    fetcher: Fetcher,
    page_sem: asyncio.Semaphore,
) -> set[str]:

    async def fetch_page(page: int) -> set[str]:
        if page == 1:
            url = start_url
        else:
            url = urljoin(start_url.rstrip("/") + "?", f"page={page}")

        async with page_sem:
            html = await fetcher.fetch(url)

        if not html:
            return set()

        soup = BeautifulSoup(html, "html.parser")
        return {
            urljoin(start_url, a["href"])
            for a in soup.select("div.thumbnail a[href]")
            if "/en/" in a["href"]
        }

    tasks = [fetch_page(p) for p in range(1, MAX_PAGES + 1)]
    results = await asyncio.gather(*tasks)

    posts = set()
    for r in results:
        if not r:
            break
        posts.update(r)

    print(f"[category] {start_url} → {len(posts)} posts")
    return posts


async def collect_all_posts(fetcher: Fetcher) -> List[str]:
    page_sem = asyncio.Semaphore(PAGE_CONCURRENCY)
    all_posts = set()

    for cat in CATEGORIES:
        posts = await collect_posts_for_category(cat, fetcher, page_sem)
        all_posts.update(posts)

    return sorted(all_posts)

# =========================
# CSV merge
# =========================

def merge_daily_csvs():
    seen, rows = set(), []

    for file in sorted(os.listdir(RAW_DIR)):
        if not file.endswith(".csv"):
            continue

        with open(os.path.join(RAW_DIR, file), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["page_url"], r["playlist_url"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(r)

    os.makedirs(os.path.dirname(MASTER_CSV), exist_ok=True)

    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["page_url", "video_code", "playlist_url", "quality", "source"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Master CSV updated: {MASTER_CSV} ({len(rows)} rows)")

# =========================
# Main
# =========================

async def main():
    async with Fetcher() as fetcher:
        post_urls = await collect_all_posts(fetcher)

        sem = asyncio.Semaphore(POST_CONCURRENCY)
        tasks = [process_post(u, fetcher, sem) for u in post_urls]
        results = await asyncio.gather(*tasks)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    os.makedirs(RAW_DIR, exist_ok=True)

    csv_path = f"{RAW_DIR}/Missav_links_{today}.csv"
    json_path = f"{RAW_DIR}/Missav_links_{today}.json"

    seen, rows = set(), []

    for item in results:
        if not item:
            continue

        page_url, playlists = item
        code = extract_video_code(page_url)

        for pl in playlists:
            key = (page_url, pl)
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "page_url": page_url,
                "video_code": code,
                "playlist_url": pl,
                "quality": infer_quality(pl),
                "source": infer_source(pl),
            })

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, rows[0].keys()).writeheader()
        csv.DictWriter(f, rows[0].keys()).writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[✓] Daily files written: {csv_path}, {json_path}")

    merge_daily_csvs()

if __name__ == "__main__":
    asyncio.run(main())
