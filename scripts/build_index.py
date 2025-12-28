#!/usr/bin/env python3
import os
import csv
import re
from datetime import datetime
from html import escape

COMBINED_FILE = os.path.join("results", "processed", "combined.csv")
DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "home.html")

ITEMS_PER_PAGE = 20

# Extract date from source file: jav_links_2025-12-28_181113.csv -> 2025-12-28
SRC_DATE_RE = re.compile(r"jav_links_(\d{4}-\d{2}-\d{2})_\d{6}\.csv$", re.IGNORECASE)


def date_from_source_file(source_file: str) -> str:
    if not source_file:
        return ""
    m = SRC_DATE_RE.search(source_file.strip())
    return m.group(1) if m else ""


def load_items():
    if not os.path.isfile(COMBINED_FILE):
        print(f"❌ Missing combined file: {COMBINED_FILE}")
        return []

    items = []
    with open(COMBINED_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("❌ combined.csv has no headers")
            return []

        if "page_url" not in reader.fieldnames or "image_url" not in reader.fieldnames:
            print("❌ combined.csv must have page_url and image_url")
            return []

        has_source = "source_file" in reader.fieldnames
        has_date_added = "date_added" in reader.fieldnames  # optional if you already have it

        for row in reader:
            page_url = (row.get("page_url") or "").strip()
            image_url = (row.get("image_url") or "").strip()

            if not page_url:
                continue

            # Prefer explicit date_added if present, else derive from source_file
            date_added = (row.get("date_added") or "").strip() if has_date_added else ""
            if not date_added and has_source:
                date_added = date_from_source_file((row.get("source_file") or "").strip())

            items.append({
                "page_url": page_url,
                "image_url": image_url,
                "date_added": date_added
            })

    return items


def build_home():
    os.makedirs(DOCS_DIR, exist_ok=True)

    items = load_items()
    if not items:
        print("ℹ️ No items to build home page.")
        return

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(items)

    def js_str(s: str) -> str:
        s = s or ""
        return (s.replace("\\", "\\\\")
                 .replace("'", "\\'")
                 .replace("\n", "\\n")
                 .replace("\r", ""))

    js_items = "[" + ",".join(
        "{page_url:'%s',image_url:'%s',date_added:'%s'}" % (
            js_str(it["page_url"]),
            js_str(it["image_url"]),
            js_str(it["date_added"]),
        ) for it in items
    ) + "]"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Home · JAV.guru</title>
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

.controls {{
  display:flex; gap:12px; flex-wrap:wrap; align-items:center;
  margin-top:14px;
}}
.controls input {{
  width:min(520px,100%);
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

.pager {{
  display:flex;
  justify-content:center;
  align-items:center;
  gap:10px;
  margin:16px 0;
  flex-wrap:wrap;
}}
.pager button {{
  padding:6px 10px;
  font-size:12px;
  border-radius:10px;
  border:1px solid var(--line);
  background:rgba(255,255,255,.03);
  color:var(--text);
  cursor:pointer;
}}
.pager button:hover {{ border-color: rgba(96,165,250,.55); }}
.pager button:disabled {{ opacity:.45; cursor:not-allowed; }}
.pager .pinfo {{ color:var(--muted); font-size:12px; }}

.grid {{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
  gap:18px;
  margin:18px 0;
}}
.card {{
  background:rgba(17,24,39,.85);
  border:1px solid var(--line);
  border-radius:16px;
  overflow:hidden;
  text-decoration:none;
  color:var(--text);
  transition:transform .2s, box-shadow .2s;
  display:block;
}}
.card:hover {{
  transform:translateY(-4px);
  box-shadow:0 10px 25px rgba(0,0,0,.4);
}}
.thumb {{
  height:200px;
  background:#000;
  display:flex;
  align-items:center;
  justify-content:center;
}}
.thumb img {{
  width:100%; height:100%;
  object-fit:cover;
  display:block;
}}
.thumb .ph {{
  width:100%; height:100%;
  background:linear-gradient(135deg,#2563eb,#22c55e);
}}
.body {{ padding:10px; }}
.url {{
  font-size:12px;
  color:var(--muted);
  word-break:break-all;
  margin-bottom:8px;
}}
.badges {{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
}}
.badge {{
  font-size:11px;
  color:var(--muted);
  border:1px solid var(--line);
  padding:5px 8px;
  border-radius:999px;
  background:rgba(255,255,255,.03);
}}
footer {{
  text-align:center;
  color:var(--muted);
  font-size:12px;
  padding:8px 0 14px;
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
  <h1>🏠 Home</h1>
  <div class="meta">{total} posts · {ITEMS_PER_PAGE}/page · Generated {escape(generated)}</div>
</header>

<div class="controls">
  <input id="q" type="text" placeholder="Filter by page_url..." autocomplete="off">
  <div class="chip" id="statusChip">0 items</div>
</div>

<div class="pager">
  <button id="prevBtn">Prev</button>
  <span class="pinfo" id="pageInfo">Page 1</span>
  <button id="nextBtn">Next</button>
</div>

<div class="grid" id="grid"></div>

<div class="pager">
  <button id="prevBtn2">Prev</button>
  <span class="pinfo" id="pageInfo2">Page 1</span>
  <button id="nextBtn2">Next</button>
</div>

<footer>Click a card to open the source page in a new tab.</footer>
</div>

<script>
const ITEMS_PER_PAGE = {ITEMS_PER_PAGE};
const allItems = {js_items};

let filtered = allItems.slice();
let page = 1;

const grid = document.getElementById('grid');
const q = document.getElementById('q');
const statusChip = document.getElementById('statusChip');

const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const prevBtn2 = document.getElementById('prevBtn2');
const nextBtn2 = document.getElementById('nextBtn2');

const pageInfo = document.getElementById('pageInfo');
const pageInfo2 = document.getElementById('pageInfo2');

function totalPages() {{
  return Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
}}
function clampPage() {{
  const tp = totalPages();
  if (page < 1) page = 1;
  if (page > tp) page = tp;
}}
function escHtml(s) {{
  return String(s)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#39;');
}}

function render() {{
  clampPage();
  const tp = totalPages();

  const start = (page - 1) * ITEMS_PER_PAGE;
  const end = start + ITEMS_PER_PAGE;
  const chunk = filtered.slice(start, end);

  statusChip.textContent = `${{filtered.length}} items (showing ${{chunk.length}})`;
  pageInfo.textContent = `Page ${{page}} / ${{tp}}`;
  pageInfo2.textContent = `Page ${{page}} / ${{tp}}`;

  prevBtn.disabled = page <= 1;
  prevBtn2.disabled = page <= 1;
  nextBtn.disabled = page >= tp;
  nextBtn2.disabled = page >= tp;

  grid.innerHTML = chunk.map(it => {{
    const pageUrl = it.page_url || '';
    const imgUrl = it.image_url || '';
    const dateAdded = it.date_added || '';

    const thumb = imgUrl
      ? `<img src="${{escHtml(imgUrl)}}" loading="lazy" alt="thumb">`
      : `<div class="ph" aria-label="no image"></div>`;

    const badge = dateAdded
      ? `<span class="badge">Added: ${{escHtml(dateAdded)}}</span>`
      : `<span class="badge">Added: —</span>`;

    return `
      <a class="card" href="${{escHtml(pageUrl)}}" target="_blank" rel="noopener noreferrer">
        <div class="thumb">${{thumb}}</div>
        <div class="body">
          <div class="url">${{escHtml(pageUrl)}}</div>
          <div class="badges">${{badge}}</div>
        </div>
      </a>
    `;
  }}).join('');
}}

function applyFilter() {{
  const term = (q.value || '').trim().toLowerCase();
  filtered = !term
    ? allItems.slice()
    : allItems.filter(it => (it.page_url || '').toLowerCase().includes(term));
  page = 1;
  render();
}}

prevBtn.addEventListener('click', () => {{ page--; render(); }});
nextBtn.addEventListener('click', () => {{ page++; render(); }});
prevBtn2.addEventListener('click', () => {{ page--; render(); }});
nextBtn2.addEventListener('click', () => {{ page++; render(); }});

q.addEventListener('input', () => {{
  window.clearTimeout(window.__t);
  window.__t = window.setTimeout(applyFilter, 120);
}});

render();
</script>
</body>
</html>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Home built: {OUTPUT_FILE}")
    print(f"   Items: {total}")
    print(f"   Source: {COMBINED_FILE}")


if __name__ == "__main__":
    build_home()
