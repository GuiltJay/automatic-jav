#!/usr/bin/env python3
import os
import csv
from datetime import datetime

RESULTS_DIR = "results"
OUTPUT_FILE = os.path.join(RESULTS_DIR, "index.html")

def build_index():
    if not os.path.isdir(RESULTS_DIR):
        print(f"❌ Results directory '{RESULTS_DIR}' not found.")
        return

    csv_files = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.endswith(".csv")],
        reverse=True
    )

    if not csv_files:
        print("ℹ️ No CSV files found in results folder.")
        return

    print(f"📂 Found {len(csv_files)} CSV files.")

    # Start HTML
    html = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <title>JAV.guru Scraper Results</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 20px; background: #f9f9f9; }",
        "    h1 { color: #333; }",
        "    ul { line-height: 1.6; }",
        "    a { text-decoration: none; color: #007acc; }",
        "    a:hover { text-decoration: underline; }",
        "    table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
        "    th, td { border: 1px solid #ccc; padding: 8px; font-size: 14px; }",
        "    th { background: #eee; }",
        "  </style>",
        "</head>",
        "<body>",
        "<h1>📊 JAV.guru Scraper Results</h1>",
        f"<p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        "<h2>Available CSV Files</h2>",
        "<ul>"
    ]

    # Link list
    for csv_file in csv_files:
        html.append(f"<li><a href='{csv_file}'>{csv_file}</a></li>")
    html.append("</ul>")

    # Show preview of the newest file
    """
    latest_file = csv_files[0]
    html.append(f"<h2>Preview of {latest_file}</h2>")
    html.append("<table>")
    try:
        with open(os.path.join(RESULTS_DIR, latest_file), newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    html.append("<tr>" + "".join(f"<th>{col}</th>" for col in row) + "</tr>")
                else:
                    html.append("<tr>" + "".join(f"<td>{col}</td>" for col in row) + "</tr>")
                if i >= 10:  # only preview first 10 rows
                    break
    except Exception as e:
        html.append(f"<tr><td colspan='2'>Error reading {latest_file}: {e}</td></tr>")
    html.append("</table>")
    """

    # End HTML
    html += ["</body>", "</html>"]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"✅ Index built at {OUTPUT_FILE}")


if __name__ == "__main__":
    build_index()
