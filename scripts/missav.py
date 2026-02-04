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

# -------------------------
# Optional engines
# -------------------------

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


# -------------------------
# Decoder utilities
# -------------------------

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
    depth = 1
    buf = []
    for ch in args:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0:
            break
        buf.append(ch)

    parts, cur, sq, dq, esc, pd = [], [], False, False, False, 0
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
        p = re.sub(r"\b" + re.escape(key) + r"\b", val, p)

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


# -------------------------
# Fetching layer
# -------------------------

@dataclass
class Fetcher:
    use_crawl4ai: bool = False
    session: Optional["aiohttp.ClientSession"] = None
    crawler: Optional["AsyncWebCrawler"] = None

    async def __aenter__(self):
        if self.use_crawl4ai:
            if not HAVE_CRAWL4AI:
                raise RuntimeError("crawl4ai not installed")
            self.crawler = AsyncWebCrawler()
            await self.crawler.__aenter__()
            return self

        if not HAVE_AIOHTTP:
            raise RuntimeError("aiohttp not installed")

        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=40, limit_per_host=15)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc, tb)
        if self.session:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            if self.crawler:
                res = await self.crawler.arun(url)
                return res.html if res.success else None
            async with self.session.get(url) as r:
                return await r.text(errors="ignore") if r.status == 200 else None
        except Exception:
            return None


# -------------------------
# Parsing helpers
# -------------------------

def extract_video_code(page_url: str) -> Optional[str]:
    m = re.search(r"/(dm\d+)(?:/|$)", page_url, re.I)
    return m.group(1).lower() if m else None


def infer_quality(playlist_url: str) -> str:
    if "1080" in playlist_url:
        return "1080p"
    if "720" in playlist_url:
        return "720p"
    if "480" in playlist_url:
        return "480p"
    return "unknown"


def infer_source(playlist_url: str) -> str:
    return urlparse(playlist_url).netloc.lower()


# -------------------------
# Workers
# -------------------------

async def process_url(url: str, fetcher: Fetcher, sem: asyncio.Semaphore):
    async with sem:
        html = await fetcher.fetch(url)
        if not html:
            return None
        decoded = decode_packed_eval(html) or html
        return url, extract_playlist_urls(decoded)


# -------------------------
# Merge daily CSVs
# -------------------------

def merge_daily_csvs(raw_dir: str, output_csv: str):
    seen = set()
    rows = []

    for file in sorted(os.listdir(raw_dir)):
        if not file.endswith(".csv"):
            continue

        path = os.path.join(raw_dir, file)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                key = (r["page_url"], r["playlist_url"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(r)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["page_url", "video_code", "playlist_url", "quality", "source"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Master CSV updated: {output_csv} ({len(rows)} rows)")


# -------------------------
# Main
# -------------------------

async def main():
    START_URL = "https://missav123.com/dm291/en/today-hot/"
    sem = asyncio.Semaphore(12)

    async with Fetcher(use_crawl4ai=False) as fetcher:
        listing_html = await fetcher.fetch(START_URL)
        if not listing_html:
            print("[!] Failed to fetch listing")
            return

        soup = BeautifulSoup(listing_html, "html.parser")
        post_urls = [
            urljoin(START_URL, a["href"])
            for a in soup.select("div.thumbnail a[href]")
            if "/en/" in a["href"]
        ]

        tasks = [process_url(u, fetcher, sem) for u in post_urls]
        results = await asyncio.gather(*tasks)

    # -------------------------
    # DAILY OUTPUT
    # -------------------------

    today = datetime.utcnow().strftime("%Y-%m-%d")
    raw_dir = os.path.join("results", "raw_missav")
    os.makedirs(raw_dir, exist_ok=True)

    csv_path = os.path.join(raw_dir, f"Missav_links_{today}.csv")
    json_path = os.path.join(raw_dir, f"Missav_links_{today}.json")

    seen = set()
    rows = []

    for item in results:
        if not item:
            continue

        page_url, playlists = item
        video_code = extract_video_code(page_url)

        for pl in playlists:
            key = (page_url, pl)
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "page_url": page_url,
                "video_code": video_code,
                "playlist_url": pl,
                "quality": infer_quality(pl),
                "source": infer_source(pl),
            })

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["page_url", "video_code", "playlist_url", "quality", "source"]
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[✓] Daily files written: {csv_path}, {json_path}")

    # -------------------------
    # MERGE TO MASTER
    # -------------------------

    merge_daily_csvs(
        raw_dir=raw_dir,
        output_csv=os.path.join("results", "processed", "missav.csv")
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
