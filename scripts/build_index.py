#!/usr/bin/env python3
import os
import csv
import re
import json
from datetime import datetime
from html import escape

COMBINED_FILE = os.path.join("results", "processed", "combined.csv")
MISSAV_JSON = os.path.join("docs", "missav.json")
DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "home.html")

ITEMS_PER_PAGE = 20

# Extract date from source file: jav_links_2025-12-28_181113.csv -> 2025-12-28
SRC_DATE_RE = re.compile(r"jav_links_(\d{4}-\d{2}-\d{2})_\d{6}\.csv$", re.IGNORECASE)
CODE_RE = re.compile(r"\b[a-z]{2,6}-\d{2,5}\b", re.IGNORECASE)


def date_from_source_file(source_file: str) -> str:
    if not source_file:
        return ""
    m = SRC_DATE_RE.search(source_file.strip())
    return m.group(1) if m else ""


def load_missav_lookup() -> dict:
    """Load missav.json and return {code_lower: entries_list}."""
    if not os.path.isfile(MISSAV_JSON):
        print("ℹ️  missav.json not found, streams will be empty")
        return {}
    try:
        with open(MISSAV_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            item["code"].strip().lower(): item.get("entries", [])
            for item in data
            if item.get("code")
        }
    except (json.JSONDecodeError, KeyError):
        return {}


def extract_code(url: str) -> str:
    """Extract first video code from a URL."""
    codes = CODE_RE.findall(url)
    return codes[0].lower() if codes else ""


def load_items():
    if not os.path.isfile(COMBINED_FILE):
        print(f"❌ Missing combined file: {COMBINED_FILE}")
        return []

    missav = load_missav_lookup()
    matched = 0

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
        has_date_added = "date_added" in reader.fieldnames

        for row in reader:
            page_url = (row.get("page_url") or "").strip()
            image_url = (row.get("image_url") or "").strip()

            if not page_url:
                continue

            date_added = (row.get("date_added") or "").strip() if has_date_added else ""
            if not date_added and has_source:
                date_added = date_from_source_file((row.get("source_file") or "").strip())

            code = extract_code(page_url)
            entries = missav.get(code, [])
            if entries:
                matched += 1

            items.append({
                "page_url": page_url,
                "image_url": image_url,
                "date_added": date_added,
                "code": code.upper(),
                "streams": entries,
            })

    print(f"ℹ️  {matched}/{len(items)} items matched with MissAV streams")
    return items


def build_home():
    os.makedirs(DOCS_DIR, exist_ok=True)

    items = load_items()
    if not items:
        print("ℹ️ No items to build home page.")
        return

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(items)
    with_streams = sum(1 for it in items if it["streams"])

    # Build JS data — use json.dumps for entries to avoid escaping issues
    js_entries = []
    for it in items:
        entry = {
            "u": it["page_url"],
            "i": it["image_url"],
            "d": it["date_added"],
            "c": it["code"],
            "s": it["streams"],
        }
        js_entries.append(entry)

    js_items = json.dumps(js_entries, separators=(",", ":"), ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Home · JAV.guru</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<style>
:root {{
  --bg:#0b0f17; --card:#111827; --line:rgba(255,255,255,.10);
  --text:#e5eefc; --muted:#93a4b8; --accent:#60a5fa;
  --green:#22c55e; --blue:#3b82f6; --orange:#f59e0b; --red:#ef4444;
  --pill-bg:#1e293b;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
  background:
    radial-gradient(1200px 700px at 20% 0%, rgba(96,165,250,0.14), transparent 60%),
    radial-gradient(900px 600px at 80% 10%, rgba(34,197,94,0.10), transparent 55%),
    var(--bg);
  color:var(--text);
  font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
}}
.wrap {{ max-width:1400px; margin:auto; padding:24px; }}

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

.top-bar {{
  display:flex; justify-content:space-between; align-items:flex-end;
  gap:12px; flex-wrap:wrap; margin-bottom:14px;
}}
h1 {{ font-size:20px; }}
.meta {{ color:var(--muted); font-size:12px; }}

.controls {{
  display:flex; gap:12px; flex-wrap:wrap; align-items:center;
  margin-bottom:14px;
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
.controls input:focus {{ border-color:var(--accent); }}
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

/* ---- GRID ---- */
.grid {{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:16px;
  margin:18px 0;
}}

/* ---- CARD ---- */
.card {{
  background:rgba(17,24,39,.85);
  border:1px solid var(--line);
  border-radius:16px;
  overflow:hidden;
  color:var(--text);
  transition:transform .2s, box-shadow .2s, border-color .2s;
  display:flex;
  flex-direction:column;
}}
.card:hover {{
  transform:translateY(-3px);
  box-shadow:0 10px 25px rgba(0,0,0,.4);
  border-color:rgba(96,165,250,.3);
}}

.card-thumb {{
  position:relative;
  aspect-ratio:16/10;
  overflow:hidden;
  cursor:pointer;
  background:#000;
}}
.card-thumb img {{
  width:100%; height:100%;
  object-fit:cover;
  display:block;
  transition:opacity .2s;
}}
.card-thumb:hover img {{ opacity:.7; }}
.card-thumb .ph {{
  width:100%; height:100%;
  background:linear-gradient(135deg,#2563eb,#22c55e);
}}

.play-overlay {{
  position:absolute; inset:0;
  display:flex; align-items:center; justify-content:center;
  opacity:0; transition:opacity .2s; pointer-events:none;
}}
.card-thumb:hover .play-overlay {{ opacity:1; }}
.play-icon {{
  width:44px; height:44px;
  background:rgba(96,165,250,0.9);
  border-radius:50%;
  display:flex; align-items:center; justify-content:center;
}}
.play-icon::after {{
  content:'';
  border-style:solid;
  border-width:7px 0 7px 12px;
  border-color:transparent transparent transparent white;
  margin-left:2px;
}}

/* ---- PLAYER ---- */
.card-player {{
  display:none;
  background:#000;
}}
.card-player video {{
  width:100%; display:block;
}}
.card-player.active {{ display:block; }}

.card-body {{ padding:10px 12px 12px; }}

.card-code {{
  font-weight:700;
  font-size:13px;
  margin-bottom:4px;
  letter-spacing:.5px;
  color:var(--accent);
}}

.card-url {{
  font-size:11px;
  color:var(--muted);
  word-break:break-all;
  margin-bottom:8px;
  line-height:1.3;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
}}

/* ---- PILLS ---- */
.pills {{
  display:flex;
  flex-wrap:wrap;
  gap:5px;
  margin-bottom:6px;
}}
.pill {{
  padding:3px 9px;
  border-radius:999px;
  font-size:10px;
  font-weight:600;
  cursor:pointer;
  border:none;
  transition:transform .1s, filter .1s;
  color:white;
}}
.pill:hover {{ transform:scale(1.05); filter:brightness(1.2); }}
.pill:active {{ transform:scale(0.97); }}

.pill-preview  {{ background:var(--pill-bg); color:var(--muted); }}
.pill-1080p    {{ background:var(--green); }}
.pill-720p     {{ background:var(--blue); }}
.pill-480p     {{ background:var(--orange); }}
.pill-playlist {{ background:var(--red); }}
.pill-other    {{ background:var(--pill-bg); color:var(--muted); }}
.pill-active   {{ outline:2px solid white; outline-offset:1px; }}

.badges {{
  display:flex; gap:6px; flex-wrap:wrap;
}}
.badge {{
  font-size:10px;
  color:var(--muted);
  border:1px solid var(--line);
  padding:4px 8px;
  border-radius:999px;
  background:rgba(255,255,255,.03);
}}
.badge-stream {{
  color:var(--green);
  border-color:rgba(34,197,94,.3);
}}

.card-link {{
  display:inline-block;
  font-size:10px;
  color:var(--accent);
  text-decoration:none;
  margin-top:6px;
}}
.card-link:hover {{ text-decoration:underline; }}

/* ---- MINI PLAYER ---- */
#miniPlayer {{
  position:fixed;
  bottom:16px; right:16px;
  width:320px;
  display:none;
  background:#000;
  border-radius:12px;
  overflow:hidden;
  box-shadow:0 8px 32px rgba(0,0,0,.7);
  z-index:1000;
  border:1px solid var(--line);
}}
#miniPlayer video {{ width:100%; display:block; }}
#miniClose {{
  position:absolute; top:6px; right:8px;
  background:rgba(0,0,0,.7);
  border:none; color:white;
  width:24px; height:24px;
  border-radius:50%; cursor:pointer;
  font-size:14px;
  display:flex; align-items:center; justify-content:center;
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
  <a href="index.html">Index</a>
  <a href="home.html">Home</a>
  <a href="codes.html">Codes</a>
  <a href="sitemap.html">Sitemap</a>
  <a href="missav.html">MissAV</a>
</nav>

<div class="top-bar">
  <h1>Home</h1>
  <div class="meta">{total} posts · {with_streams} with streams · Generated {escape(generated)}</div>
</div>

<div class="controls">
  <input id="q" type="text" placeholder="Filter by URL or code..." autocomplete="off">
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

<footer>Click thumbnail to play best stream. Use pills to switch quality.</footer>
</div>

<div id="miniPlayer">
  <button id="miniClose">&times;</button>
  <video controls></video>
</div>

<script>
const ITEMS_PER_PAGE = {ITEMS_PER_PAGE};
const IMAGE_PROXY = "https://imgproxy.mrspidyxd.workers.dev/?url=";
const allItems = {js_items};

let filtered = allItems.slice();
let page = 1;

let activeHls = null;
let activeVideo = null;
let activeCard = null;
let miniHls = null;
let miniActive = false;

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

/* ---- RENDER ---- */

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

  grid.innerHTML = '';
  chunk.forEach(it => grid.appendChild(buildCard(it)));
}}

/* ---- BUILD CARD ---- */

function buildCard(it) {{
  const pageUrl = it.u || '';
  const imgUrl = it.i || '';
  const dateAdded = it.d || '';
  const code = it.c || '';
  const streams = it.s || [];
  const hasStreams = streams.length > 0;

  const card = document.createElement('div');
  card.className = 'card';

  // Thumbnail
  const thumbDiv = document.createElement('div');
  thumbDiv.className = 'card-thumb';
  if (imgUrl) {{
    thumbDiv.innerHTML = `<img src="${{escHtml(IMAGE_PROXY + encodeURIComponent(imgUrl))}}" loading="lazy" alt="${{escHtml(code)}}" onerror="this.outerHTML='<div class=ph></div>'"><div class="play-overlay"><div class="play-icon"></div></div>`;
  }} else {{
    thumbDiv.innerHTML = '<div class="ph"></div>';
  }}

  // Player area
  const playerDiv = document.createElement('div');
  playerDiv.className = 'card-player';
  const video = document.createElement('video');
  video.controls = true;
  video.playsInline = true;
  video.preload = 'none';
  playerDiv.appendChild(video);

  // Body
  const body = document.createElement('div');
  body.className = 'card-body';

  // Code
  if (code) {{
    const codeDiv = document.createElement('div');
    codeDiv.className = 'card-code';
    codeDiv.textContent = code;
    body.appendChild(codeDiv);
  }}

  // Stream pills
  if (hasStreams) {{
    const pills = document.createElement('div');
    pills.className = 'pills';

    // Preview pill
    const preview = `https://fourhoi.com/${{code.toLowerCase()}}/preview.mp4`;
    const prevPill = document.createElement('button');
    prevPill.className = 'pill pill-preview';
    prevPill.textContent = 'Preview';
    prevPill.onclick = (e) => {{ e.stopPropagation(); playSource(card, video, playerDiv, thumbDiv, preview, 'direct', prevPill, pills); }};
    pills.appendChild(prevPill);

    // Quality pills sorted: 1080p > 720p > 480p > playlist
    const order = {{ '1080p':0, '720p':1, '480p':2, 'playlist':3 }};
    const sorted = [...streams].sort((a,b) => (order[a.quality]??4) - (order[b.quality]??4));

    for (const e of sorted) {{
      const pill = document.createElement('button');
      const qClass = ['1080p','720p','480p','playlist'].includes(e.quality) ? 'pill-'+e.quality : 'pill-other';
      pill.className = 'pill ' + qClass;
      pill.textContent = e.quality || 'stream';
      pill.title = e.source || '';
      pill.onclick = (ev) => {{ ev.stopPropagation(); playSource(card, video, playerDiv, thumbDiv, e.url, 'hls', pill, pills); }};
      pills.appendChild(pill);
    }}

    body.appendChild(pills);

    // Thumbnail click -> play best stream
    thumbDiv.onclick = () => {{
      const best = streams.find(e => e.quality==='1080p')
                || streams.find(e => e.quality==='720p')
                || streams[0];
      playSource(card, video, playerDiv, thumbDiv, best.url, 'hls', null, body.querySelector('.pills'));
    }};
  }} else {{
    // No streams: thumbnail links to page
    thumbDiv.onclick = () => window.open(pageUrl, '_blank');
    thumbDiv.title = 'Open source page';
  }}

  // URL display
  const urlDiv = document.createElement('div');
  urlDiv.className = 'card-url';
  urlDiv.textContent = pageUrl;
  body.appendChild(urlDiv);

  // Badges
  const badges = document.createElement('div');
  badges.className = 'badges';

  if (dateAdded) {{
    const b = document.createElement('span');
    b.className = 'badge';
    b.textContent = dateAdded;
    badges.appendChild(b);
  }}

  if (hasStreams) {{
    const b = document.createElement('span');
    b.className = 'badge badge-stream';
    b.textContent = streams.length + ' stream' + (streams.length > 1 ? 's' : '');
    badges.appendChild(b);
  }}

  body.appendChild(badges);

  // Source link
  const link = document.createElement('a');
  link.className = 'card-link';
  link.href = pageUrl;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.textContent = 'Open source page';
  link.onclick = (e) => e.stopPropagation();
  body.appendChild(link);

  card.appendChild(thumbDiv);
  card.appendChild(playerDiv);
  card.appendChild(body);
  return card;
}}

/* ---- PLAY SOURCE ---- */

function playSource(card, video, playerDiv, thumbDiv, url, type, activePill, pillsContainer) {{
  if (activeVideo && activeVideo !== video) {{
    stopVideo(activeVideo);
  }}
  closeMini();

  if (pillsContainer) {{
    pillsContainer.querySelectorAll('.pill').forEach(p => p.classList.remove('pill-active'));
  }}
  if (activePill) activePill.classList.add('pill-active');

  if (activeHls) {{ activeHls.destroy(); activeHls = null; }}

  playerDiv.classList.add('active');
  thumbDiv.style.display = 'none';

  if (type === 'hls' && url.includes('.m3u8')) {{
    if (Hls.isSupported()) {{
      const hls = new Hls({{ enableWorker:true, lowLatencyMode:false }});
      hls.loadSource(url);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(()=>{{}}));
      hls.on(Hls.Events.ERROR, (_, data) => {{
        if (data.fatal) {{
          hls.destroy();
          video.src = url;
          video.play().catch(()=>{{}});
        }}
      }});
      activeHls = hls;
    }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
      video.src = url;
      video.play().catch(()=>{{}});
    }}
  }} else {{
    video.src = url;
    video.play().catch(()=>{{}});
  }}

  activeVideo = video;
  activeCard = card;
}}

function stopVideo(video) {{
  video.pause();
  video.removeAttribute('src');
  video.load();
  const card = video.closest('.card');
  if (card) {{
    const pd = card.querySelector('.card-player');
    const td = card.querySelector('.card-thumb');
    if (pd) pd.classList.remove('active');
    if (td) td.style.display = '';
    card.querySelectorAll('.pill-active').forEach(p => p.classList.remove('pill-active'));
  }}
}}

/* ---- MINI PLAYER ---- */

const miniEl = document.getElementById('miniPlayer');
const miniVideo = miniEl.querySelector('video');
document.getElementById('miniClose').onclick = closeMini;

function closeMini() {{
  if (miniHls) {{ miniHls.destroy(); miniHls = null; }}
  miniVideo.pause();
  miniVideo.removeAttribute('src');
  miniEl.style.display = 'none';
  miniActive = false;
}}

window.addEventListener('scroll', () => {{
  if (!activeVideo || !activeCard) return;
  const rect = activeCard.getBoundingClientRect();
  const offscreen = rect.bottom < -50 || rect.top > window.innerHeight + 50;

  if (offscreen && !miniActive) {{
    miniActive = true;
    miniEl.style.display = 'block';
    if (activeHls) {{
      if (miniHls) miniHls.destroy();
      const src = activeHls.url;
      miniHls = new Hls({{ enableWorker:true }});
      miniHls.loadSource(src);
      miniHls.attachMedia(miniVideo);
      miniHls.on(Hls.Events.MANIFEST_PARSED, () => {{
        miniVideo.currentTime = activeVideo.currentTime;
        miniVideo.play().catch(()=>{{}});
      }});
    }} else {{
      miniVideo.src = activeVideo.src;
      miniVideo.currentTime = activeVideo.currentTime;
      miniVideo.play().catch(()=>{{}});
    }}
    activeVideo.pause();
  }} else if (!offscreen && miniActive) {{
    activeVideo.currentTime = miniVideo.currentTime;
    activeVideo.play().catch(()=>{{}});
    closeMini();
  }}
}}, {{ passive:true }});

/* ---- FILTER + PAGER ---- */

function applyFilter() {{
  const term = (q.value || '').trim().toLowerCase();
  filtered = !term
    ? allItems.slice()
    : allItems.filter(it => {{
        const hay = (it.u + ' ' + it.c).toLowerCase();
        return hay.includes(term);
      }});
  page = 1;
  render();
}}

prevBtn.addEventListener('click', () => {{ page--; render(); }});
nextBtn.addEventListener('click', () => {{ page++; render(); }});
prevBtn2.addEventListener('click', () => {{ page--; render(); }});
nextBtn2.addEventListener('click', () => {{ page++; render(); }});

q.addEventListener('input', () => {{
  window.clearTimeout(window.__t);
  window.__t = window.setTimeout(applyFilter, 150);
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
    print(f"   With streams: {with_streams}")
    print(f"   Source: {COMBINED_FILE}")


if __name__ == "__main__":
    build_home()
