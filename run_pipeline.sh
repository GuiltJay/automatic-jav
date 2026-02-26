#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "🚀 JAV.guru Pipeline Started"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
RESULTS_DIR="$ROOT_DIR/results"
RAW_DIR="$RESULTS_DIR/raw"
PROCESSED_DIR="$RESULTS_DIR/processed"
DOCS_DIR="$ROOT_DIR/docs"

echo "📁 Project root:   $ROOT_DIR"
echo "📁 Scripts dir:    $SCRIPTS_DIR"
echo "📁 Results dir:    $RESULTS_DIR"
echo "📁 Raw dir:        $RAW_DIR"
echo "📁 Processed dir:  $PROCESSED_DIR"
echo "📁 Docs dir:       $DOCS_DIR"
echo

mkdir -p "$RAW_DIR" "$PROCESSED_DIR" "$DOCS_DIR"

run_py () {
  local script="$1"
  if [[ -f "$script" ]]; then
    echo "▶️  python3 $(basename "$script")"
    python3 "$script"
    echo
  else
    echo "⚠️  Missing: $script (skipping)"
    echo
  fi
}

# ----------------------------------------
# 1) Scrape -> results/raw/
# ----------------------------------------
run_py "$SCRIPTS_DIR/scraper.py"

# ----------------------------------------
# 2) Dedupe/filter (optional)
# ----------------------------------------
run_py "$SCRIPTS_DIR/dupe_filter.py"

# ----------------------------------------
# 3) Combine -> results/processed/combined.csv
# (This step is REQUIRED for codes + sitemap builders if they read combined.csv)
# ----------------------------------------
if [[ -f "$SCRIPTS_DIR/build_index.py" ]]; then
  echo "▶️  python3 build_index.py (combine -> processed/combined.csv)"
  python3 "$SCRIPTS_DIR/build_index.py"
  echo
else
  echo "❌ Missing required script: $SCRIPTS_DIR/build_index.py"
  exit 1
fi

# Sanity check: combined.csv should exist now
if [[ ! -f "$PROCESSED_DIR/combined.csv" ]]; then
  echo "❌ Expected combined file not found: $PROCESSED_DIR/combined.csv"
  echo "   Your build_index.py should write to results/processed/combined.csv"
  exit 1
fi

# ----------------------------------------
# 4) Build codes page -> docs/codes.html
# ----------------------------------------
run_py "$SCRIPTS_DIR/build_codes.py"

# ----------------------------------------
# 5) Build sitemap page -> docs/sitemap.html
# ----------------------------------------
run_py "$SCRIPTS_DIR/build_sitemap.py"

# ----------------------------------------
# 6) Build SEO & Stats
# ----------------------------------------
run_py "$SCRIPTS_DIR/build_seo.py"
run_py "$SCRIPTS_DIR/build_stats.py"

# ----------------------------------------
# Done
# ----------------------------------------
echo "========================================"
echo "✅ Pipeline finished successfully"
echo "🌐 GitHub Pages entry: docs/index.html"
echo "   - Codes:   docs/codes.html"
echo "   - Sitemap: docs/sitemap.html"
echo "   - Data:    results/processed/combined.csv"
echo "========================================"
