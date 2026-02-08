import csv
import html
from collections import defaultdict
from pathlib import Path

INPUT_CSV = "results/processed/missav.csv"
OUTPUT_HTML = "docs/missav.html"
PAGE_SIZE = 50


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MissAV Viewer</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

<style>
body {{
  background:#0f1117;
  color:#e6e6e6;
  font-family:system-ui,sans-serif;
  margin:0;
  padding:20px;
}}

input {{
  width:100%;
  padding:10px;
  margin-bottom:10px;
  border-radius:6px;
  border:none;
  background:#1c1f26;
  color:#fff;
}}

.video {{
  border:1px solid #2a2e38;
  border-radius:8px;
  margin-bottom:12px;
  padding:12px;
}}

.header {{
  font-weight:700;
  font-size:18px;
  margin-bottom:6px;
}}

.links a {{
  margin-right:10px;
  color:#4da3ff;
  cursor:pointer;
}}

.player {{
  display:none;
  margin-top:10px;
}}

.pagination {{
  margin-top:20px;
  text-align:center;
}}

button {{
  background:#1c1f26;
  color:#fff;
  border:none;
  padding:8px 12px;
  margin:2px;
  border-radius:5px;
  cursor:pointer;
}}
</style>
</head>

<body>

<h1>MissAV CSV Viewer</h1>

<input id="filter" placeholder="Search video code / source / quality">

<div id="container"></div>

<div class="pagination" id="pagination"></div>

<script>
const DATA = {data};
const PAGE_SIZE = {page_size};
let page = 1;

function getParams() {{
  return new URLSearchParams(window.location.search);
}}

function applyDeepLink() {{
  const p = getParams();
  if (p.get("code")) document.getElementById("filter").value = p.get("code");
  if (p.get("source")) document.getElementById("filter").value = p.get("source");
}}

function render() {{
  const q = document.getElementById("filter").value.toLowerCase();
  let filtered = DATA.filter(v =>
    v.code.includes(q) ||
    v.entries.some(e =>
      e.source.includes(q) || e.quality.includes(q)
    )
  );

  const pages = Math.ceil(filtered.length / PAGE_SIZE);
  page = Math.min(page, pages) || 1;

  const start = (page - 1) * PAGE_SIZE;
  const slice = filtered.slice(start, start + PAGE_SIZE);

  const c = document.getElementById("container");
  c.innerHTML = "";

  slice.forEach(v => {{
    const div = document.createElement("div");
    div.className = "video";

    let links = v.entries.map(e =>
      `<a onclick="play('${e.url}')">${e.quality} (${e.source})</a>`
    ).join("");

    div.innerHTML = `
      <div class="header">${v.code}</div>
      <div class="links">${links}</div>
      <video controls class="player"></video>
    `;
    c.appendChild(div);
  }});

  renderPagination(pages);
}}

function renderPagination(pages) {{
  const p = document.getElementById("pagination");
  p.innerHTML = "";

  for (let i=1;i<=pages;i++) {{
    const b = document.createElement("button");
    b.innerText = i;
    if (i === page) b.style.background = "#4da3ff";
    b.onclick = () => {{ page=i; render(); }};
    p.appendChild(b);
  }}
}}

function play(url) {{
  document.querySelectorAll(".player").forEach(v => v.style.display="none");

  const v = event.target.closest(".video").querySelector("video");
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

document.getElementById("filter").oninput = () => {{
  page = 1;
  render();
}};

applyDeepLink();
render();
</script>

</body>
</html>
"""


def generate():
    grouped = defaultdict(list)

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            grouped[r["video_code"]].append({
                "url": r["playlist_url"],
                "quality": r["quality"],
                "source": r["source"],
            })

    data = [
        {
            "code": k.lower(),
            "entries": v,
        }
        for k, v in sorted(grouped.items())
    ]

    Path(OUTPUT_HTML).parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(
            HTML.format(
                data=json.dumps(data),
                page_size=PAGE_SIZE,
            )
        )

    print(f"[✓] UI generated: {OUTPUT_HTML}")


if __name__ == "__main__":
    generate()
