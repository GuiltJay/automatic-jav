#!/usr/bin/env python3
import os
import csv
import re
from datetime import datetime
from html import escape
from urllib.parse import urlsplit

COMBINED_FILE = os.path.join("results", "processed", "combined.csv")
DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "sitemap.html")

# Prefer deriving date from source_file like: jav_links_2025-12-28_181113.csv -> 2025-12-28
SRC_DATE_RE = re.compile(r"jav_links_(\d{4}-\d{2}-\d{2})_\d{6}\.csv$", re.IGNORECASE)


def date_from_source_file(source_file: str) -> str:
    if not source_file:
        return ""
    m = SRC_DATE_RE.search(source_file.strip())
    return m.group(1) if m else ""


def host_from_url(url: str) -> str:
    try:
        return (urlsplit(url).netloc or "").lower()
    except Exception:
        return ""


def load_rows():
    if not os.path.isfile(COMBINED_FILE):
        print(f"❌ Missing combined file: {COMBINED_FILE}")
        return []

    rows = []
    with open(COMBINED_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("❌ combined.csv has no headers")
            return []
        if "page_url" not in reader.fieldnames:
            print("❌ combined.csv must have page_url")
            return []

        has_source = "source_file" in reader.fieldnames
        has_date_added = "date_added" in reader.fieldnames

        for row in reader:
            page_url = (row.get("page_url") or "").strip()
            if not page_url:
                continue

            # Prefer date_added column if present; else derive from source_file
            date_added = (row.get("date_added") or "").strip() if has_date_added else ""
            if not date_added and has_source:
                date_added = date_from_source_file((row.get("source_file") or "").strip())

            rows.append({
                "page_url": page_url,
                "date_added": date_added,
                "host": host_from_url(page_url),
            })

    # newest-first by date_added (YYYY-MM-DD sorts lexicographically), then by URL
    rows.sort(key=lambda r: (r["date_added"] or "", r["page_url"]), reverse=True)
    return rows


def build_sitemap():
    os.makedirs(DOCS_DIR, exist_ok=True)

    rows = load_rows()
    if not rows:
        print("ℹ️ No rows found to build sitemap.")
        return

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    items = []
    for r in rows:
        d = r["date_added"] or "—"
        host = r["host"] or "link"
        items.append(
            f"<li>"
            f"  <span class='date'>{escape(d)}</span>"
            f"  <a class='url' href='{escape(r['page_url'])}' target='_blank' rel='noopener noreferrer'>{escape(r['page_url'])}</a>"
            f"  <span class='host'>{escape(host)}</span>"
            f"</li>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sitemap · JAV.guru</title>
<style>
:root {{
  --bg:#0b0f17; --card:#111827; --line:rgba(255,255,255,.10);
  --text:#e5eefc; --muted:#93a4b8; --accent:#60a5fa;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:
    radial-gradient(1200px 700px at 20% 0%, rgba(96,165,250,0.14), transparent 60%),
    radial-gradient(900px 600px at 80% 10%, rgba(34,197,94,0.10), transparent 55%),
    var(--bg);
  color:var(--text);
  font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
}}
.wrap {{ max-width:1200px; margin:auto; padding:24px; }}

nav {{
  display:flex; gap:10px; flex-wrap:wrap;
  align-items:center; margin-bottom:14px;
}}
nav a {{
  color:var(--muted);
  text-decoration:none;
  border:1px solid var(--line);
  padding:8px 10px;
  border-radius:999px;
  background:rgba(255,255,255,.03);
  font-size:12px;
}}
nav a:hover {{ color:var(--accent); border-color:rgba(96,165,250,.5); }}

header {{
  display:flex; justify-content:space-between; align-items:flex-end;
  gap:12px; flex-wrap:wrap;
}}
h1 {{ margin:0; font-size:20px; }}
.meta {{ color:var(--muted); font-size:12px; }}

.card {{
  margin-top:14px;
  background:rgba(17,24,39,.85);
  border:1px solid var(--line);
  border-radius:16px;
  padding:14px;
  box-shadow:0 10px 25px rgba(0,0,0,.35);
}}

.controls {{
  display:flex;
  gap:12px;
  align-items:center;
  flex-wrap:wrap;
  margin: 10px 0 14px;
}}
.controls input {{
  width:min(560px, 100%);
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--line);
  background:rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
  font-size:13px;
}}
.controls .chip {{
  font-size:12px;
  color:var(--muted);
  border:1px solid var(--line);
  padding:8px 10px;
  border-radius:999px;
  background:rgba(255,255,255,.03);
  white-space:nowrap;
}}

ul {{
  margin:0;
  padding:0;
  list-style:none;
}}

li {{
  display:grid;
  grid-template-columns: 110px 1fr 180px;
  gap:12px;
  align-items:center;
  padding:10px 8px;
  border-bottom:1px solid rgba(255,255,255,.06);
}}
li:last-child {{ border-bottom:none; }}

.date {{
  color:var(--muted);
  font-size:12px;
  border:1px solid var(--line);
  padding:5px 8px;
  border-radius:999px;
  width:fit-content;
  background:rgba(255,255,255,.03);
}}

.url {{
  color:var(--text);
  text-decoration:none;
  word-break:break-all;
  font-size:13px;
}}
.url:hover {{
  color:var(--accent);
  text-decoration:underline;
}}

.host {{
  color:var(--muted);
  font-size:12px;
  text-align:right;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}}

@media (max-width: 900px) {{
  li {{ grid-template-columns: 110px 1fr; }}
  .host {{ display:none; }}
}}
</style>
</head>
<body>
<div class="wrap">

<nav>
  <a href="index.html">⬅ Index</a>
  <a href="home.html">🏠 Home</a>
  <a href="codes.html">🏷️ Codes</a>
  <a href="sitemap.html">🗺️ Sitemap</a>
</nav>

<header>
  <h1>🗺️ Sitemap</h1>
  <div class="meta">{len(rows)} links · Generated {escape(generated)}</div>
</header>

<div class="card">
  <div class="controls">
    <input id="q" type="text" placeholder="Filter links..." autocomplete="off">
    <div class="chip" id="count">{len(rows)} items</div>
  </div>

  <ul id="list">
    {''.join(items)}
  </ul>
</div>

</div>

<script>
const q = document.getElementById('q');
const list = document.getElementById('list');
const count = document.getElementById('count');
const rows = Array.from(list.querySelectorAll('li'));

q.addEventListener('input', () => {{
  const term = (q.value || '').trim().toLowerCase();
  let shown = 0;
  rows.forEach(li => {{
    const t = li.textContent.toLowerCase();
    const ok = !term || t.includes(term);
    li.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  count.textContent = `${{shown}} items`;
}});
</script>
</body>
</html>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Sitemap built: {OUTPUT_FILE}")
    print(f"   Links: {len(rows)}")
    print(f"   Source: {COMBINED_FILE}")


if __name__ == "__main__":
    build_sitemap()
