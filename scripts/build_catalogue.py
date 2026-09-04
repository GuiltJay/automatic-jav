#!/usr/bin/env python3
"""
Build compact, high-performance catalogue JSON feed for the Browse page.
Reduces client payload from ~19MB down to ~650KB.
"""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone

DOCS_DIR = "docs"
RESULTS_DIR = os.path.join("results", "processed")
OUTPUT_FILE = os.path.join(DOCS_DIR, "catalogue.json")
CODE_RE = re.compile(r"\b[a-z]{2,6}-\d{2,5}\b", re.IGNORECASE)


def extract_code(url: str) -> str:
    m = CODE_RE.findall(url or "")
    return m[0].upper() if m else ""


def build_catalogue():
    os.makedirs(DOCS_DIR, exist_ok=True)
    items: list[dict] = []
    seen_urls: set[str] = set()

    # 1. Load MissAV lookup for streams
    missav_path = os.path.join(DOCS_DIR, "missav.json")
    missav_lookup: dict[str, list[dict]] = {}
    missav_data: list[dict] = []
    if os.path.isfile(missav_path):
        try:
            with open(missav_path, encoding="utf-8") as f:
                missav_data = json.load(f)
            for it in missav_data:
                c = (it.get("code") or "").strip().upper()
                if c and "entries" in it:
                    missav_lookup[c] = it["entries"][:2]
        except Exception:
            pass

    # 2. JAV.guru items (from combined.csv)
    combined_path = os.path.join(RESULTS_DIR, "combined.csv")
    guru_count = 0
    if os.path.isfile(combined_path):
        with open(combined_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = (row.get("page_url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                code = extract_code(url)
                streams = missav_lookup.get(code, [])
                items.append({
                    "c": code,
                    "t": code or "JAV.guru Media",
                    "u": url,
                    "i": (row.get("image_url") or "").strip(),
                    "s": "jav.guru",
                    "st": streams,
                    "d": (row.get("date_added") or "").strip(),
                })
                guru_count += 1
                if guru_count >= 1000:
                    break

    # 3. MissAV items (direct video stream entries)
    missav_count = 0
    for it in missav_data:
        code = (it.get("code") or "").strip().upper()
        if not code:
            continue
        page_url = f"https://missav123.com/dm291/en/{code.lower()}"
        if page_url in seen_urls:
            continue
        seen_urls.add(page_url)
        items.append({
            "c": code,
            "t": f"{code} MissAV Stream",
            "u": page_url,
            "i": f"https://fourhoi.com/{code.lower()}/cover-n.jpg",
            "s": "missav",
            "st": it.get("entries", [])[:2],
            "d": (it.get("date_added") or "").strip(),
        })
        missav_count += 1
        if missav_count >= 800:
            break

    # 4. OneJAV items
    onejav_path = os.path.join(RESULTS_DIR, "onejav.csv")
    onejav_count = 0
    if os.path.isfile(onejav_path):
        with open(onejav_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                url = (row.get("page_url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                code = (row.get("code") or extract_code(url)).strip().upper()
                items.append({
                    "c": code,
                    "t": (row.get("title") or code).strip(),
                    "u": url,
                    "i": (row.get("image_url") or "").strip(),
                    "s": "onejav",
                    "tor": (row.get("torrent_url") or "").strip(),
                    "sz": (row.get("size") or "").strip(),
                    "act": (row.get("actresses") or "").strip(),
                    "st": missav_lookup.get(code, []),
                    "d": (row.get("date") or "").strip(),
                })
                onejav_count += 1
                if onejav_count >= 600:
                    break

    # 5. JavCT items
    javct_path = os.path.join(RESULTS_DIR, "javct.csv")
    javct_count = 0
    if os.path.isfile(javct_path):
        with open(javct_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                url = (row.get("page_url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                code = (row.get("code") or extract_code(url)).strip().upper()
                items.append({
                    "c": code,
                    "t": (row.get("title") or code).strip(),
                    "u": url,
                    "i": (row.get("image_url") or "").strip(),
                    "s": "javct",
                    "v": (row.get("views") or "").strip(),
                    "st": missav_lookup.get(code, []),
                    "d": (row.get("date_scraped") or "").strip(),
                })
                javct_count += 1
                if javct_count >= 400:
                    break

    envelope = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": items,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(envelope, f, separators=(",", ":"))

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"✅ Generated compact catalogue: {OUTPUT_FILE} ({len(items)} items, {size_kb:.1f} KB)")


if __name__ == "__main__":
    build_catalogue()
