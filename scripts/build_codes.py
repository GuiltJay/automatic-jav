#!/usr/bin/env python3
import os
import csv
import re
from datetime import datetime
from html import escape

# =========================
# CONFIG
# =========================
RESULTS_DIR = "results/processed"
INPUT_FILE = os.path.join(RESULTS_DIR, "combined.csv")
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "codes.html")

PAGE_COL = "page_url"

# match codes like: dldss-436, ipx-123, abcd-9999
CODE_RE = re.compile(r"\b[a-z]{2,6}-\d{2,5}\b", re.IGNORECASE)


# =========================
# LOAD + EXTRACT CODES
# =========================
def extract_codes_from_combined():
    if not os.path.isfile(INPUT_FILE):
        print(f"❌ combined.csv not found at {INPUT_FILE}")
        return []

    codes = set()

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or PAGE_COL not in reader.fieldnames:
            print(f"❌ '{PAGE_COL}' column not found in combined.csv")
            return []

        for row in reader:
            text = (row.get(PAGE_COL) or "").lower()
            for m in CODE_RE.findall(text):
                codes.add(m.upper())

    return sorted(codes)


# =========================
# BUILD SINGLE HTML
# =========================
def build_html(codes):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(codes)

    items = "\n".join(
        f"<div class='code' onclick=\"copy('{escape(code)}')\">{escape(code)}</div>"
        for code in codes
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Code Index</title>
<style>
:root {{
  --bg:#0b0f17;
  --card:#111827;
  --line:rgba(255,255,255,.1);
  --text:#e5eefc;
  --muted:#93a4b8;
  --accent:#60a5fa;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
}}
.wrap {{
  max-width:1000px;
  margin:auto;
  padding:24px;
}}
header {{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:12px;
  flex-wrap:wrap;
}}
h1 {{
  margin:0;
  font-size:22px;
}}
.meta {{
  font-size:12px;
  color:var(--muted);
}}
.controls {{
  margin-top:14px;
}}
.controls input {{
  width:100%;
  max-width:420px;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--line);
  background:rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
}}
.controls input::placeholder {{
  color:rgba(147,164,184,.7);
}}
.grid {{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
  gap:12px;
  margin-top:20px;
}}
.code {{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:12px;
  padding:14px 10px;
  text-align:center;
  font-weight:600;
  letter-spacing:.4px;
  font-size:14px;
  cursor:pointer;
  user-select:none;
  transition:border-color .15s,color .15s,transform .15s;
}}
.code:hover {{
  border-color:var(--accent);
  color:var(--accent);
  transform:translateY(-2px);
}}
footer {{
  margin-top:26px;
  font-size:12px;
  color:var(--muted);
  text-align:center;
}}
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>📚 Code Index</h1>
  <div class="meta">{total} codes · Generated {escape(generated)}</div>
</header>

<div class="controls">
  <input id="search" type="text" placeholder="Search code..." />
</div>

<div class="grid" id="grid">
{items}
</div>

<footer>Source: combined.csv · Click a code to copy</footer>

</div>

<script>
const allCodes = [...document.querySelectorAll('.code')];

document.getElementById('search').addEventListener('input', e => {{
  const q = e.target.value.toLowerCase();
  allCodes.forEach(el => {{
    el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}});

function copy(text) {{
  navigator.clipboard.writeText(text);
}}
</script>

</body>
</html>
"""


# =========================
# MAIN
# =========================
def build():
    codes = extract_codes_from_combined()
    if not codes:
        print("ℹ️ No codes found.")
        return

    html = build_html(codes)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Code index built at {OUTPUT_FILE}")
    print(f"   Codes found: {len(codes)}")
    print(f"   Source: {INPUT_FILE}")


if __name__ == "__main__":
    build()
