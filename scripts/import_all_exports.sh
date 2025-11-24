#!/usr/bin/env bash
# Bulk-import every CSV in exports/ using the existing Django import command.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Optional override: scripts/import_all_exports.sh [path-to-exports]
EXPORT_DIR="${1:-exports}"

if [ ! -d "$EXPORT_DIR" ]; then
  echo "Export directory not found: $EXPORT_DIR" >&2
  exit 1
fi

if [ -f venv/bin/activate ]; then
  # Activate virtualenv if available so Django dependencies are present.
  source venv/bin/activate
fi

shopt -s nullglob
mapfile -t csv_files < <(ls -1 "$EXPORT_DIR"/*.csv 2>/dev/null | sort)
shopt -u nullglob

if [ ${#csv_files[@]} -eq 0 ]; then
  echo "No CSV files found in $EXPORT_DIR"
  exit 0
fi

echo "Importing ${#csv_files[@]} CSV files from $EXPORT_DIR"
for csv_path in "${csv_files[@]}"; do
  echo "-> $csv_path"
  python backend/manage.py import_daily_csv "$csv_path" --source-name steam_daily
done

echo "All imports completed."
