#!/usr/bin/env bash
set -euo pipefail
echo "========================================"
echo "🌟 JavCT Pipeline Started"
echo "========================================"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
RESULTS_DIR="$ROOT_DIR/results"
RAW_DIR="$RESULTS_DIR/raw_javct"
PROCESSED_DIR="$RESULTS_DIR/processed"
DOCS_DIR="$ROOT_DIR/docs"

cd "$ROOT_DIR"
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

# 1) Scrape JavCT
run_py "$SCRIPTS_DIR/javct.py"

# Sanity check
if ! ls "$RAW_DIR"/*/*.csv >/dev/null 2>&1; then
  echo "❌ No JavCT CSV files found in $RAW_DIR"
  exit 1
fi

# 2) Build UIs
run_py "$SCRIPTS_DIR/build_javct.py"
run_py "$SCRIPTS_DIR/build_models.py"

# Sanity check
if [[ ! -f "$DOCS_DIR/javct.html" || ! -f "$DOCS_DIR/models.html" ]]; then
  echo "❌ Expected output HTML not found."
  exit 1
fi

echo "========================================"
echo "✅ JavCT Pipeline Finished"
echo "🌐 Outputs:"
echo "   - docs/javct.html"
echo "   - docs/models.html"
echo "========================================"
