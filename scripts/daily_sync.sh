#!/bin/bash
set -euo pipefail
cd /home/ec2-user/steam_scraper
source venv/bin/activate
mkdir -p logs

# 1) 抓取并导出 CSV
python steam_daily.py >> logs/steam_daily.log 2>&1

# 2) 把当日 CSV 导入 Django
today=$(date -u +%F)  # steam_daily.py 用 UTC 命名文件
csv_path="exports/new_games_${today}.csv"
# 如果按日文件不存在，兜底用最新一份
if [ ! -f "$csv_path" ]; then
  csv_path=$(ls -1t exports/new_games_*.csv | head -n 1)
fi

python backend/manage.py import_daily_csv "$csv_path" \
  --ingested-date "$today" \
  --source-name steam_daily >> logs/import_daily.log 2>&1

