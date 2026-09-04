#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "📊 Aggregator Pipeline Started"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"

cd "$ROOT_DIR"

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

# Build codes page
run_py "$SCRIPTS_DIR/build_codes.py"

# Build sitemap page & exports
run_py "$SCRIPTS_DIR/build_sitemap.py"

# Build SEO & Stats
run_py "$SCRIPTS_DIR/build_seo.py"
run_py "$SCRIPTS_DIR/build_stats.py"

# Build compact catalogue feed for browse page
run_py "$SCRIPTS_DIR/build_catalogue.py"

# Refresh Home with newly extracted streams
run_py "$SCRIPTS_DIR/build_index.py"

echo "========================================"
echo "✅ Aggregator Pipeline finished successfully"
echo "========================================"
