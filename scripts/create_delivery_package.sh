#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="steam_scraper"
DATE_STAMP="$(date +%Y%m%d)"
COMMIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
DELIVERY_VERSION="${1:-${DATE_STAMP}-${COMMIT_SHA}}"
STAGE_ROOT="$ROOT_DIR/.delivery"
PACKAGE_DIR="$STAGE_ROOT/${PROJECT_NAME}-${DELIVERY_VERSION}"
ZIP_PATH="$ROOT_DIR/${PROJECT_NAME}-delivery-${DELIVERY_VERSION}.zip"

copy_path() {
  local source_path="$1"
  local destination_dir="$PACKAGE_DIR"

  mkdir -p "$destination_dir/$(dirname "$source_path")"
  cp -R "$ROOT_DIR/$source_path" "$destination_dir/$source_path"
}

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# Top-level source and docs
copy_path "README.md"
copy_path ".env.example"
copy_path ".gitignore"
copy_path "requirements.txt"
copy_path "steam_daily.py"
copy_path "steam_recent_tag_scraper.py"
copy_path "steam_search_tag_scraper.py"
copy_path "steam_unreleased_tags_scraper.py"
copy_path "steam_tag_specific_scraper.py"
copy_path "steam_comprehensive_tag_scraper.py"
copy_path "run_unreleased_tags_scraper.py"
copy_path "backfill_merge.py"
copy_path "generate-mock-data.js"

# Backend
copy_path "backend/manage.py"
copy_path "backend/core"
copy_path "backend/steam_selection"

# Frontend
copy_path "frontend/.env.example"
copy_path "frontend/index.html"
copy_path "frontend/package.json"
copy_path "frontend/pnpm-lock.yaml"
copy_path "frontend/postcss.config.js"
copy_path "frontend/start-demo.bat"
copy_path "frontend/start-demo.sh"
copy_path "frontend/tailwind.config.ts"
copy_path "frontend/tsconfig.json"
copy_path "frontend/tsconfig.node.json"
copy_path "frontend/vite.config.ts"
copy_path "frontend/src"

# Utility scripts
copy_path "scripts/create_delivery_package.sh"
copy_path "scripts/daily_sync.sh"
copy_path "scripts/import_all_exports.sh"

cat > "$PACKAGE_DIR/DELIVERY_MANIFEST.txt" <<EOF
Project: ${PROJECT_NAME}
Delivery version: ${DELIVERY_VERSION}
Source commit: ${COMMIT_SHA}
Packaged at: $(date '+%Y-%m-%d %H:%M:%S %Z')

Included:
- backend source code and Django migrations
- frontend source code and dependency manifests
- crawler scripts
- packaging and import scripts
- README.md
- .env.example files

Excluded:
- .git/
- .env
- backend/db.sqlite3
- venv/
- frontend/node_modules/
- frontend/dist/
- logs, pid files, local caches, exports
- steam_data/ and steam_data_current/ cache snapshots

Acceptance commands:
1. python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
2. cd backend && python manage.py migrate && python manage.py check
3. cd ../frontend && npm install && npm run build

Notes:
- Runtime secrets must be provided via .env based on the shipped example files.
- SQLite database contents are intentionally not included in the delivery package.
EOF

chmod 755 "$PACKAGE_DIR/scripts/"*.sh "$PACKAGE_DIR/frontend/start-demo.sh" 2>/dev/null || true

find "$PACKAGE_DIR" \
  \( -name '__pycache__' -o -name '.DS_Store' -o -name '._*' \) \
  -exec rm -rf {} +
find "$PACKAGE_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

rm -f "$ZIP_PATH"
python3 - <<PY
from pathlib import Path
import zipfile

stage_root = Path(r"$STAGE_ROOT")
package_dir = Path(r"$PACKAGE_DIR")
zip_path = Path(r"$ZIP_PATH")

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(package_dir.rglob("*")):
        if path.is_dir():
            continue
        zf.write(path, path.relative_to(stage_root))
PY

echo "Created delivery package:"
echo "$ZIP_PATH"
