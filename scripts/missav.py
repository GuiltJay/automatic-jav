from __future__ import annotations

from urllib.parse import urljoin
from bs4 import BeautifulSoup
import asyncio
import random
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple
import os

# Try importing crawl4ai.AsyncWebCrawler, otherwise we'll use aiohttp
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


# ------------------------- Decoder utilities -------------------------

def unquote_js_string(s: str) -> str:
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        inner = s[1:-1]
    else:
        inner = s
    return inner.encode("utf-8").decode("unicode_escape")


def int_to_base(n: int, base: int) -> str:
    if n == 0:
        return "0"
    digits = []
    while n > 0:
        d = n % base
        digits.append(str(d) if d < 10 else chr(ord("a") + d - 10))
        n //= base
    return "".join(reversed(digits))


def decode_packed_eval(payload: str) -> Optional[str]:
    start_marker = "eval(function(p,a,c,k,e,d)"
    start = payload.find(start_marker)
    if start == -1:
        return None

    chunk = payload[start:start + 20000]

    marker = "return p}("
    idx = chunk.find(marker)
    if idx == -1:
        idx = chunk.find(")(", 0)
        if idx == -1:
            return None
        start_args = idx + 2
    else:
        start_args = idx + len(marker)

    depth = 1
    i = start_args
    while i < len(chunk) and depth > 0:
        ch = chunk[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return None

    args_str = chunk[start_args:i - 1]

    parts: List[str] = []
    cur: List[str] = []
    in_sq = in_dq = False
    esc = False
    paren_depth = 0

    for ch in args_str:
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            cur.append(ch)
            esc = True
            continue
        if ch == "'" and not in_dq:
            in_sq = not in_sq
            cur.append(ch)
            continue
        if ch == '"' and not in_sq:
            in_dq = not in_dq
            cur.append(ch)
            continue
        if ch == "(" and not in_sq and not in_dq:
            paren_depth += 1
            cur.append(ch)
            continue
        if ch == ")" and not in_sq and not in_dq:
            paren_depth -= 1
            cur.append(ch)
            continue
        if ch == "," and not in_sq and not in_dq and paren_depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)

    if cur:
        parts.append("".join(cur).strip())

    if len(parts) < 4:
        return None

    p_part = parts[0]
    try:
        a = int(parts[1])
        c = int(parts[2])
    except Exception:
        return None
    k_part = parts[3]

    try:
        p = unquote_js_string(p_part)
    except Exception:
        p = p_part.strip("'\"")

    m = re.match(
        r"('(?:\\'|[^'])*'|\"(?:\\\"|[^\"])*\")\.split\('\\|'\)",
        k_part
    )
    if m:
        k_string = unquote_js_string(m.group(1))
    else:
        q = k_part.split(".split")[0].strip()
        k_string = unquote_js_string(q)

    k = k_string.split("|")

    decoded = p
    for n in range(c - 1, -1, -1):
        key = int_to_base(n, a)
        val = k[n] if n < len(k) and k[n] != "" else key
        decoded = re.sub(r"\b" + re.escape(key) + r"\b", val, decoded)

    return decoded


def extract_playlist_urls(text: str) -> List[str]:
    patterns = [
        r"https?://[A-Za-z0-9\-\._/~%]+\.m3u8(?:\?[^\s'\"<>]+)?",
        r"https?://[A-Za-z0-9\-\._/~%]+/playlist(?:\.\w+)?(?:\?[^\s'\"<>]+)?",
    ]
    out: List[str] = []
    seen = set()
    for pat in patterns:
        for u in re.findall(pat, text):
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


# ------------------------- Fetching layer -------------------------

@dataclass
class Fetcher:
    """
    One shared fetcher for ALL requests (listing + details).
    By default, uses aiohttp for speed (connection pooling).
    If you want crawl4ai, set use_crawl4ai=True.
    """
    use_crawl4ai: bool = False
    session: Optional["aiohttp.ClientSession"] = None
    crawler: Optional["AsyncWebCrawler"] = None

    async def __aenter__(self) -> "Fetcher":
        if self.use_crawl4ai:
            if not HAVE_CRAWL4AI:
                raise RuntimeError("use_crawl4ai=True but crawl4ai is not installed.")
            self.crawler = AsyncWebCrawler()
            await self.crawler.__aenter__()
            return self

        if not HAVE_AIOHTTP:
            raise RuntimeError("aiohttp is not installed, cannot run in fast mode.")

        import aiohttp
        timeout = aiohttp.ClientTimeout(total=30)

        connector = aiohttp.TCPConnector(
            limit=50,           # total connections
            limit_per_host=20,  # per-host connections
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.crawler is not None:
            await self.crawler.__aexit__(exc_type, exc, tb)
        if self.session is not None:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            if self.crawler is not None:
                res = await self.crawler.arun(url)
                if not getattr(res, "success", False):
                    return None
                return getattr(res, "html", "") or ""

            assert self.session is not None
            async with self.session.get(url, allow_redirects=True) as resp:
                # Treat non-200 as failure for crawling
                if resp.status != 200:
                    return None
                # Let aiohttp pick encoding
                return await resp.text(errors="ignore")

        except asyncio.CancelledError:
            raise
        except Exception:
            return None


async def fetch_with_retries(
    fetcher: Fetcher,
    url: str,
    retries: int = 3,
    base_delay: float = 0.6,
    max_delay: float = 6.0,
) -> Optional[str]:
    """
    Exponential backoff + jitter.
    """
    for attempt in range(retries + 1):
        html = await fetcher.fetch(url)
        if html:
            return html

        if attempt < retries:
            delay = min(max_delay, base_delay * (2 ** attempt))
            delay = delay * (0.8 + 0.4 * random.random())  # jitter
            await asyncio.sleep(delay)

    return None


# ------------------------- Parsing -------------------------

def extract_posts(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    posts = set()

    for card in soup.select("div.thumbnail"):
        a = card.select_one("a[href]")
        if not a:
            continue
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if "/en/" in href:
            posts.add(href)

    return sorted(posts)


def find_next_page_url(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    link_next = soup.select_one('link[rel="next"][href]')
    if link_next:
        return urljoin(base_url, link_next["href"].strip())

    a_rel_next = soup.select_one('a[rel="next"][href]')
    if a_rel_next:
        return urljoin(base_url, a_rel_next["href"].strip())

    a_aria_next = soup.select_one('a[aria-label*="Next"][href], a[aria-label*="next"][href]')
    if a_aria_next:
        return urljoin(base_url, a_aria_next["href"].strip())

    a_class_next = soup.select_one('.pagination a.next[href], nav[aria-label*="pagination"] a.next[href]')
    if a_class_next:
        return urljoin(base_url, a_class_next["href"].strip())

    for a in soup.select("a[href]"):
        txt = (a.get_text() or "").strip().lower()
        if txt in {"next", "older", "›", "»", "next ›", "next »"}:
            return urljoin(base_url, a["href"].strip())

    return None


# ------------------------- Orchestrator -------------------------

async def process_url(url: str, fetcher: Fetcher, sem: asyncio.Semaphore) -> Tuple[str, List[str]]:
    async with sem:
        html = await fetch_with_retries(fetcher, url, retries=3)
        if not html:
            return (url, [])

        decoded = decode_packed_eval(html)
        if decoded:
            urls = extract_playlist_urls(decoded)
            if urls:
                return (url, urls)

        return (url, extract_playlist_urls(html))


async def crawl_listing_posts(
    start_url: str,
    fetcher: Fetcher,
    max_pages: int = 10,
) -> list[str]:
    all_posts: set[str] = set()
    seen_pages: set[str] = set()

    url = start_url
    page_num = 0

    while url and url not in seen_pages and page_num < max_pages:
        seen_pages.add(url)
        page_num += 1

        html = await fetch_with_retries(fetcher, url, retries=3)
        if not html:
            print(f"[!] Listing fetch failed: {url}")
            break

        posts = extract_posts(html)
        for p in posts:
            all_posts.add(urljoin(url, p))  # normalize -> absolute

        print(f"[page {page_num}] {url} -> {len(posts)} posts (total unique: {len(all_posts)})")

        url = find_next_page_url(html, base_url=url)

    return sorted(all_posts)


async def main() -> None:
    START_URL = "https://jav.guru/page/5/"
    max_pages = 50

    concurrency = 12  # aiohttp can handle higher; lower if you get 429s
    sem = asyncio.Semaphore(concurrency)

    # Fast default: aiohttp shared session
    # If you MUST use crawl4ai: set True
    use_crawl4ai = False

    async with Fetcher(use_crawl4ai=use_crawl4ai) as fetcher:
        # Phase 1: crawl listings
        target_urls = await crawl_listing_posts(START_URL, fetcher, max_pages=max_pages)
        print(f"\nCollected {len(target_urls)} unique post URLs\n")

        if not target_urls:
            print("[!] No post URLs found; exiting.")
            return

        # Phase 2: process posts concurrently
        tasks = [process_url(u, fetcher, sem) for u in target_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Output
    for item in results:
        if isinstance(item, Exception):
            print(f"[!] Task error: {item}", file=sys.stderr)
            continue
        DOCS_DIR = "docs"
        OUTPUT_FILE = os.path.join(DOCS_DIR,"Missav_links.txt")

        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
          for item in results:
                if isinstance(item, Exception):
                    continue

                page_url, urls = item
                if not urls:
                    continue

                f.write(f"{page_url}\n")
                for u in urls:
                    if "missav" in u or "playlist" in u:
                        f.write(f"{u}\n")
                f.write("\n")
                f.flush()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise
