import csv
import json
from collections import defaultdict, Counter
from pathlib import Path

INPUT_CSV = "results/processed/missav.csv"
OUTPUT_HTML = "docs/missav.html"
PAGE_SIZE = 25   # mobile-friendly

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MissAV Viewer</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

<style>
:root {{
  --bg:#0f1117;
  --card:#151820;
  --muted:#9aa4b2;
  --accent:#4da3ff;
}}

* {{ box-sizing:border-box; }}

body {{
  margin:0;
  background:var(--bg);
  color:#fff;
  font-family:system-ui,sans-serif;
  padding:12px;
}}

h1 {{
  font-size:20px;
  margin:6px 0 10px;
}}

input {{
  width:100%;
  padding:12px;
  border-radius:8px;
  border:none;
  background:#1c1f26;
  color:#fff;
  margin-bottom:12px;
  font-size:16px;
}}

.stats {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:8px;
  margin-bottom:12px;
}}

.stat {{
  background:var(--card);
  padding:10px;
  border-radius:8px;
  font-size:13px;
}}

.stat b {{
  display:block;
  font-size:18px;
}}

.video {{
  background:var(--card);
  border-radius:10px;
  padding:12px;
  margin-bottom:12px;
}}

.code {{
  font-weight:700;
  font-size:16px;
  margin-bottom:6px;
}}

.tags {{
  font-size:12px;
  color:var(--muted);
  margin-bottom:6px;
}}

.links a {{
  display:inline-block;
  margin:4px 6px 4px 0;
  padding:6px 10px;
  background:#1c1f26;
  border-radius:20px;
  font-size:12px;
  color:var(--accent);
  text-decoration:none;
}}

video {{
  width:100%;
  margin-top:8px;
  border-radius:8px;
  display:none;
}}

.pagination {{
  display:flex;
  flex-wrap:wrap;
  justify-content:center;
  gap:6px;
  margin:16px 0;
}}

button {{
  background:#1c1f26;
  color:#fff;
  border:none;
  padding:8px 12px;
  border-radius:6px;
  font-size:14px;
}}

button.active {{
  background:var(--accent);
}}
</style>
</head>

<body>

<h1>MissAV Viewer</h1>

<input id="filter" placeholder="Search video code / source / quality">

<div class="stats" id="stats"></div>
<div id="container"></div>
<div class="pagination" id="pagination"></div>

<script>
const DATA = {data};
const STATS = {stats};
const PAGE_SIZE = {page_size};
let page = 1;

function getParams() {{
  return new URLSearchParams(location.search);
}}

function applyDeepLink() {{
  const p = getParams();
  if (p.get("code")) filter.value = p.get("code");
  if (p.get("source")) filter.value = p.get("source");
}}

function renderStats(filtered) {{
  const el = document.getElementById("stats");
  el.innerHTML = `
    <div class="stat"><b>${filtered.length}</b>Videos</div>
    <div class="stat"><b>${STATS.total_streams}</b>Streams</div>
    <div class="stat"><b>${STATS.qualities.join(", ")}</b>Qualities</div>
    <div class="stat"><b>${STATS.sources.join(", ")}</b>Sources</div>
  `;
}}

function render() {{
  const q = filter.value.toLowerCase();
  let filtered = DATA.filter(v =>
    v.code.includes(q) ||
    v.entries.some(e =>
      e.source.includes(q) || e.quality.includes(q)
    )
  );

  renderStats(filtered);

  const pages = Math.ceil(filtered.length / PAGE_SIZE);
  page = Math.min(page, pages) || 1;

  const start = (page - 1) * PAGE_SIZE;
  const slice = filtered.slice(start, start + PAGE_SIZE);

  container.innerHTML = "";

  slice.forEach(v => {{
    const d = document.createElement("div");
    d.className = "video";

    const links = v.entries.map(e =>
      `<a onclick="play(this,'${e.url}')">${e.quality} · ${e.source}</a>`
    ).join("");

    d.innerHTML = `
      <div class="code">${v.code}</div>
      <div class="tags">${v.entries.length} streams</div>
      <div class="links">${links}</div>
      <video controls></video>
    `;
    container.appendChild(d);
  }});

  renderPagination(pages);
}}

function renderPagination(pages) {{
  pagination.innerHTML = "";
  for (let i=1;i<=pages;i++) {{
    const b = document.createElement("button");
    b.textContent = i;
    if (i===page) b.className="active";
    b.onclick = () => {{ page=i; render(); }};
    pagination.appendChild(b);
  }}
}}

function play(el,url) {{
  document.querySelectorAll("video").forEach(v => v.style.display="none");
  const v = el.closest(".video").querySelector("video");
  v.style.display="block";

  if (Hls.isSupported()) {{
    const hls = new Hls();
    hls.loadSource(url);
    hls.attachMedia(v);
  }} else {{
    v.src = url;
  }}
  v.play();
}}

filter.oninput = () => {{ page=1; render(); }};
applyDeepLink();
render();
</script>

</body>
</html>
"""


def generate():
    grouped = defaultdict(list)
    qualities = Counter()
    sources = Counter()

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            grouped[r["video_code"]].append({
                "url": r["playlist_url"],
                "quality": r["quality"],
                "source": r["source"],
            })
            qualities[r["quality"]] += 1
            sources[r["source"]] += 1

    data = [
        {"code": k.lower(), "entries": v}
        for k, v in sorted(grouped.items())
    ]

    stats = {
        "total_streams": sum(qualities.values()),
        "qualities": sorted(qualities),
        "sources": sorted(sources),
    }

    Path(OUTPUT_HTML).parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(HTML.format(
            data=json.dumps(data),
            stats=json.dumps(stats),
            page_size=PAGE_SIZE,
        ))

    print(f"[✓] Mobile UI generated → {OUTPUT_HTML}")


if __name__ == "__main__":
    generate()
