#!/usr/bin/env bash
set -euo pipefail
echo "========================================"
echo "🧲 OneJAV Pipeline Started"
echo "========================================"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
RESULTS_DIR="$ROOT_DIR/results"
RAW_DIR="$RESULTS_DIR/raw_onejav"
PROCESSED_DIR="$RESULTS_DIR/processed"
DOCS_DIR="$ROOT_DIR/docs"

# ✅ Ensure working directory is the project root
cd "$ROOT_DIR"

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
# 1) Scrape OneJAV -> results/raw_onejav/
# ----------------------------------------
run_py "$SCRIPTS_DIR/onejav.py"
# Sanity check
if ! ls "$RAW_DIR"/*/*.csv >/dev/null 2>&1; then
  echo "❌ No OneJAV CSV files found in $RAW_DIR"
  exit 1
fi
# ----------------------------------------
# 2) Build OneJAV UI -> docs/onejav.html
# ----------------------------------------
run_py "$SCRIPTS_DIR/build_onejav.py"
# Sanity check
if [[ ! -f "$DOCS_DIR/onejav.html" ]]; then
  echo "❌ Expected output not found: docs/onejav.html"
  exit 1
fi
if [[ ! -f "$DOCS_DIR/onejav.json" ]]; then
  echo "❌ Expected output not found: docs/onejav.json"
  exit 1
fi
# ----------------------------------------
# Done
# ----------------------------------------
echo "========================================"
echo "✅ OneJAV Pipeline Finished"
echo "🌐 Output:"
echo "   - UI:     docs/onejav.html"
echo "   - Data:   docs/onejav.json"
echo "   - Raw:    results/raw_onejav/"
echo "   - Master: results/processed/onejav.csv"
echo "========================================"
