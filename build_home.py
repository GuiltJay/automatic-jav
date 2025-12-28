#!/usr/bin/env python3
import os
import csv
import math
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from html import escape

RESULTS_DIR = "results"
OUTPUT_DIR = os.path.join(RESULTS_DIR, "")
ITEMS_PER_PAGE = 20

PAGE_COL = "page_url"
IMAGE_COL = "image_url"

def normalize_url(url: str) -> str:
    if url is None:
        return ""
    url = url.strip()
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        scheme = (parts.scheme or "").lower()
        netloc = (parts.netloc or "").lower()
        fragment = ""  # drop fragments

        drop = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "gclid", "fbclid"
        }
        q = [(k, v) for (k, v) in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in drop]
        query = urlencode(sorted(q), doseq=True)

        return urlunsplit((scheme, netloc, parts.path, query, fragment))
    except Exception:
        return url

def list_csv_files(results_dir: str):
    files = [f for f in os.listdir(results_dir) if f.lower().endswith(".csv")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(results_dir, f)), reverse=True)
    return files

def load_items_from_all_csvs(results_dir: str):
    """
    Loads rows from all CSVs, dedupes by normalized page_url.
    Keeps newest row if duplicate found (by file mtime).
    Returns: list of dict items with page_url, image_url, source_file, source_mtime
    """
    csv_files = list_csv_files(results_dir)
    if not csv_files:
        return []

    seen = {}  # key=normalized_page_url -> (file_mtime, item_dict)

    for fname in csv_files:
        path = os.path.join(results_dir, fname)
        mtime = os.path.getmtime(path)

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                continue
            if PAGE_COL not in reader.fieldnames or IMAGE_COL not in reader.fieldnames:
                # skip files that don't match your schema
                continue

            for row in reader:
                page_url = (row.get(PAGE_COL) or "").strip()
                image_url = (row.get(IMAGE_COL) or "").strip()

                norm_page = normalize_url(page_url)
                if not norm_page:
                    continue

                item = {
                    "page_url": page_url,
                    "image_url": image_url,
                    "normalized_page_url": norm_page,
                    "source_file": fname,
                    "source_mtime": mtime,
                }

                if norm_page in seen:
                    prev_mtime, _prev_item = seen[norm_page]
                    if mtime > prev_mtime:
                        seen[norm_page] = (mtime, item)
                else:
                    seen[norm_page] = (mtime, item)

    # newest first
    items = [v[1] for v in sorted(seen.values(), key=lambda t: t[0], reverse=True)]
    return items

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "page"), exist_ok=True)

def rel_link_for_page(page_num: int):
    """
    We generate:
      index.html for page 1 at OUTPUT_DIR/index.html
      page 2 at OUTPUT_DIR/page/2/index.html
    """
    if page_num == 1:
        return "./index.html"
    return f"./page/{page_num}/index.html"

def pagination_html(current: int, total_pages: int):
    # show a compact window of page numbers
    window = 3
    start = max(1, current - window)
    end = min(total_pages, current + window)

    parts = ["<nav class='pager'>"]

    # Prev
    if current > 1:
        parts.append(f"<a class='btn' href='{escape(rel_link_for_page(current-1))}'>← Prev</a>")
    else:
        parts.append("<span class='btn disabled'>← Prev</span>")

    # Page numbers
    def page_link(p):
        cls = "pnum current" if p == current else "pnum"
        return f"<a class='{cls}' href='{escape(rel_link_for_page(p))}'>{p}</a>"

    if start > 1:
        parts.append(page_link(1))
        if start > 2:
            parts.append("<span class='dots'>…</span>")

    for p in range(start, end + 1):
        parts.append(page_link(p))

    if end < total_pages:
        if end < total_pages - 1:
            parts.append("<span class='dots'>…</span>")
        parts.append(page_link(total_pages))

    # Next
    if current < total_pages:
        parts.append(f"<a class='btn' href='{escape(rel_link_for_page(current+1))}'>Next →</a>")
    else:
        parts.append("<span class='btn disabled'>Next →</span>")

    parts.append("</nav>")
    return "\n".join(parts)

def render_page(items, page_num: int, total_pages: int, generated_at: str):
    title = "Scraper Results"
    pager_top = pagination_html(page_num, total_pages)
    pager_bottom = pager_top

    rows = []
    for i, it in enumerate(items, start=1 + (page_num - 1) * ITEMS_PER_PAGE):
        page_url = it["page_url"]
        image_url = it["image_url"]

        # A little robustness: if image_url missing, show placeholder box
        thumb = (
            f"<img class='thumb' src='{escape(image_url)}' loading='lazy' alt='thumbnail' />"
            if image_url else
            "<div class='thumb ph' aria-label='no image'></div>"
        )

        rows.append(f"""
        <li class="item">
          <a class="thumbwrap" href="{escape(page_url)}" target="_blank" rel="noopener noreferrer">
            {thumb}
          </a>
          <div class="meta">
            <a class="plink" href="{escape(page_url)}" target="_blank" rel="noopener noreferrer">{escape(page_url)}</a>
            <div class="sub">
              <span class="label">Image:</span>
              {"<a class='ilink' href='" + escape(image_url) + "' target='_blank' rel='noopener noreferrer'>" + escape(image_url) + "</a>" if image_url else "<span class='muted'>(none)</span>"}
            </div>
            <div class="sub muted small">#{i} · source: {escape(it["source_file"])}</div>
          </div>
        </li>
        """.strip())

    rows_html = "\n".join(rows) if rows else "<p class='muted'>No items.</p>"

    # IMPORTANT: rel links work from any page because we always use ./page/N/index.html relative to site root.
    # But when you're inside /page/N/, "./page/.." isn't correct.
    # Solution: we generate links relative to site root? Easiest: use absolute-from-root style paths without leading slash?
    #
    # We'll instead compute links as:
    # - from page1: "./page/2/index.html"
    # - from pageN: "../2/index.html" etc.
    #
    # To keep it simple, we’ll generate each page with its own correct link function below in build_site().
    # So here we just accept already-correct pager HTML; build_site will pass a per-page pager.

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)} · Page {page_num}</title>
  <style>
    :root {{
      --bg: #0b0f17;
      --card: #111827;
      --muted: #93a4b8;
      --text: #e5eefc;
      --line: rgba(255,255,255,0.10);
      --accent: #60a5fa;
    }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Apple Color Emoji","Segoe UI Emoji";
      background: radial-gradient(1200px 700px at 20% 0%, rgba(96,165,250,0.14), transparent 60%),
                  radial-gradient(900px 600px at 80% 10%, rgba(34,197,94,0.10), transparent 55%),
                  var(--bg);
      color: var(--text);
    }}
    .wrap {{
      max-width: 980px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0.2px;
    }}
    .metaTop {{
      color: var(--muted);
      font-size: 12px;
    }}
    .card {{
      background: rgba(17,24,39,0.82);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.25);
      overflow: hidden;
    }}
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      gap: 12px;
      flex-wrap: wrap;
    }}
    .chip {{
      font-size: 12px;
      color: var(--muted);
      border: 1px solid var(--line);
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.03);
    }}

    ul.list {{
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .item {{
      display: grid;
      grid-template-columns: 88px 1fr;
      gap: 12px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      align-items: center;
    }}
    .item:last-child {{ border-bottom: none; }}
    .thumbwrap {{
      display: block;
      width: 88px;
      height: 60px;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.04);
    }}
    .thumb {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .thumb.ph {{
      width: 100%;
      height: 100%;
      display: block;
      background:
        linear-gradient(135deg, rgba(96,165,250,0.18), rgba(34,197,94,0.10));
    }}
    .plink {{
      color: var(--text);
      text-decoration: none;
      font-size: 13px;
      word-break: break-all;
    }}
    .plink:hover {{ color: var(--accent); text-decoration: underline; }}
    .sub {{
      margin-top: 6px;
      font-size: 12px;
      word-break: break-all;
    }}
    .label {{ color: var(--muted); margin-right: 6px; }}
    .ilink {{
      color: rgba(96,165,250,0.9);
      text-decoration: none;
    }}
    .ilink:hover {{ text-decoration: underline; }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 11px; }}

    .pager {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: center;
    }}
    .btn {{
      font-size: 12px;
      padding: 7px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      color: var(--text);
      text-decoration: none;
    }}
    .btn:hover {{ border-color: rgba(96,165,250,0.55); }}
    .btn.disabled {{
      opacity: 0.45;
      pointer-events: none;
    }}
    .pnum {{
      font-size: 12px;
      padding: 7px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
      color: var(--text);
      text-decoration: none;
    }}
    .pnum.current {{
      background: rgba(96,165,250,0.18);
      border-color: rgba(96,165,250,0.45);
    }}
    .dots {{
      color: var(--muted);
      padding: 0 4px;
    }}
    footer {{
      margin-top: 14px;
      text-align: center;
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>🧩 Mini List · {escape(title)}</h1>
      <div class="metaTop">Generated: {escape(generated_at)} · Page {page_num} / {total_pages}</div>
    </header>

    <div class="card">
      <div class="toolbar">
        <div class="chip">Showing {len(items)} items · {ITEMS_PER_PAGE} per page</div>
        {pager_top}
      </div>

      <ul class="list">
        {rows_html}
      </ul>

      <div class="toolbar">
        <div class="chip">End of page</div>
        {pager_bottom}
      </div>
    </div>

    <footer>Static site output in <code>{escape(OUTPUT_DIR)}</code></footer>
  </div>
</body>
</html>
"""
    return html

def build_site():
    ensure_dirs()

    items = load_items_from_all_csvs(RESULTS_DIR)
    if not items:
        print("ℹ️ No items found (no matching CSVs with page_url & image_url).")
        return

    total_pages = max(1, math.ceil(len(items) / ITEMS_PER_PAGE))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write a per-page link function that works from that page's folder:
    def page_href(from_page: int, to_page: int) -> str:
        """
        Returns correct relative href from current page folder.
        Page 1 lives at: site/index.html
        Page N lives at: site/page/N/index.html
        """
        if from_page == 1:
            # we're at site/
            if to_page == 1:
                return "./index.html"
            return f"./page/{to_page}/index.html"

        # we're at site/page/{from_page}/
        if to_page == 1:
            return "../../index.html"
        # to another page folder
        if to_page == from_page:
            return "./index.html"
        return f"../{to_page}/index.html"

    def pagination_html_from(from_page: int, current: int, total_pages: int) -> str:
        window = 3
        start = max(1, current - window)
        end = min(total_pages, current + window)

        parts = ["<nav class='pager'>"]

        # Prev
        if current > 1:
            parts.append(f"<a class='btn' href='{escape(page_href(from_page, current-1))}'>← Prev</a>")
        else:
            parts.append("<span class='btn disabled'>← Prev</span>")

        def pnum(p):
            cls = "pnum current" if p == current else "pnum"
            return f"<a class='{cls}' href='{escape(page_href(from_page, p))}'>{p}</a>"

        if start > 1:
            parts.append(pnum(1))
            if start > 2:
                parts.append("<span class='dots'>…</span>")

        for p in range(start, end + 1):
            parts.append(pnum(p))

        if end < total_pages:
            if end < total_pages - 1:
                parts.append("<span class='dots'>…</span>")
            parts.append(pnum(total_pages))

        # Next
        if current < total_pages:
            parts.append(f"<a class='btn' href='{escape(page_href(from_page, current+1))}'>Next →</a>")
        else:
            parts.append("<span class='btn disabled'>Next →</span>")

        parts.append("</nav>")
        return "\n".join(parts)

    # Build each page
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_items = items[start:end]

        # render with correct per-page pager
        pager = pagination_html_from(page_num, page_num, total_pages)
        html = render_page(page_items, page_num, total_pages, generated_at)
        # patch in correct pager (render_page already includes pager; easiest: replace both navs)
        # We'll just regenerate final html by replacing the first occurrence of "<nav class='pager'>"
        # BUT better: do a simple replace of the placeholder pager rendered earlier.
        # Since render_page currently uses pagination_html() which isn't correct for nested dirs,
        # we'll brute replace all pager blocks by the correct one:
        html = html.replace("<nav class='pager'>", "<nav class='pager'>", 1)  # no-op, keep structure
        # safer: just overwrite pager sections by locating them is messy; easiest: render again with correct pager:
        # We'll do a simple replace of the toolbar pager segments using marker strings:
        # Markers are stable: "<div class=\"toolbar\"> ... {pager_top}"
        # Instead: render_page was built with pager_top=... inside. We'll just re-create the page with correct pager
        # by injecting pager into the html using string replacement of the first nav, and then the second:
        # Replace first pager block:
        first_start = html.find("<nav class='pager'>")
        if first_start != -1:
            first_end = html.find("</nav>", first_start)
            if first_end != -1:
                html = html[:first_start] + pager + html[first_end+6:]
        # Replace second pager block:
        second_start = html.find("<nav class='pager'>")
        if second_start != -1:
            second_end = html.find("</nav>", second_start)
            if second_end != -1:
                html = html[:second_start] + pager + html[second_end+6:]

        # Write to proper path
        if page_num == 1:
            out_path = os.path.join(OUTPUT_DIR, "index.html")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        else:
            out_dir = os.path.join(OUTPUT_DIR, "page", str(page_num))
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "index.html")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    print("✅ Site built")
    print(f"   Items: {len(items)}")
    print(f"   Pages: {total_pages} (20 per page)")
    print(f"   Entry: {os.path.join(OUTPUT_DIR, 'index.html')}")

if __name__ == "__main__":
    build_site()
