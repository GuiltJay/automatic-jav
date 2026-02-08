#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "🎬 MissAV Pipeline Started"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
RESULTS_DIR="$ROOT_DIR/results"
RAW_DIR="$RESULTS_DIR/raw_missav"
PROCESSED_DIR="$RESULTS_DIR/processed"
DOCS_DIR="$ROOT_DIR/docs"

echo "📁 Project root:   $ROOT_DIR"
echo "📁 Scripts dir:    $SCRIPTS_DIR"
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
    echo "❌ Missing required script: $script"
    exit 1
  fi
}

# ----------------------------------------
# 1) Scrape MissAV -> results/raw_missav/
# ----------------------------------------
run_py "$SCRIPTS_DIR/missav.py"

# Sanity check
if ! ls "$RAW_DIR"/*.csv >/dev/null 2>&1; then
  echo "❌ No MissAV CSV files found in $RAW_DIR"
  exit 1
fi

# ----------------------------------------
# 2) Build MissAV UI -> docs/missav.html
# ----------------------------------------
run_py "$SCRIPTS_DIR/build_missav.py"

# Sanity check
if [[ ! -f "$DOCS_DIR/missav.html" ]]; then
  echo "❌ Expected output not found: docs/missav.html"
  exit 1
fi

# ----------------------------------------
# Done
# ----------------------------------------
echo "========================================"
echo "✅ MissAV Pipeline Finished"
echo "🌐 Output:"
echo "   - UI:     docs/missav.html"
echo "   - Raw:    results/raw_missav/"
echo "   - Master: results/processed/missav.csv"
echo "========================================"
