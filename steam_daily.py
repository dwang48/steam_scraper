import os
import json
import csv
import smtplib
import tempfile
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import List, Dict
import logging
from dateutil import parser as dateparser

import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Constants
APPLIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
DETAILS_URL_TEMPLATE = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
DATA_DIR = Path(__file__).parent / "steam_data"
EXPORT_DIR = Path(__file__).parent / "exports"
KNOWN_APPS_FILE = DATA_DIR / "applist.json"

FIELDS = [
    "type",
    "name",
    "steam_appid",
    "developers",
    "publishers",
    "header_image",
    "website",
    "categories",
    "genres",
    "steam_url",
]

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# Load local .env if available
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("steam_daily")

MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "32"))

def fetch_full_applist() -> List[Dict]:
    """Download the full Steam app list."""
    resp = requests.get(APPLIST_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("applist", {}).get("apps", [])

def load_known_appids() -> set:
    if KNOWN_APPS_FILE.exists():
        with KNOWN_APPS_FILE.open("r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_known_appids(app_ids: set):
    with KNOWN_APPS_FILE.open("w", encoding="utf-8") as f:
        json.dump(sorted(app_ids), f)

def fetch_app_details(appid: int) -> Dict:
    url = DETAILS_URL_TEMPLATE.format(appid=appid)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json().get(str(appid), {})
        if not data.get("success"):
            return {}
        return data.get("data", {})
    except Exception:
        return {}

def build_row(details: Dict) -> Dict:
    if not details:
        return {}
    
    # Filter to only include unreleased games (coming_soon: true) that have store pages
    release_info = details.get("release_date", {})
    if not release_info.get("coming_soon", False):  # Skip already released games
        return {}
    
    return {
        "type": details.get("type"),
        "name": details.get("name"),
        "steam_appid": details.get("steam_appid"),
        "developers": ";".join(details.get("developers", [])) if details.get("developers") else None,
        "header_image": details.get("header_image"),
        "website": details.get("website"),
        "publishers": ";".join(details.get("publishers", [])) if details.get("publishers") else None,
        "categories": ";".join(c.get("description") for c in details.get("categories", [])) if details.get("categories") else None,
        "genres": ";".join(g.get("description") for g in details.get("genres", [])) if details.get("genres") else None,
        "steam_url": f"https://store.steampowered.com/app/{details.get('steam_appid')}" if details.get("steam_appid") else None,
    }

def export_csv(rows: List[Dict]) -> Path:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = EXPORT_DIR / f"new_games_{today_str}.csv"
    with file_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return file_path

def send_email(csv_path: Path):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    to_email = os.environ.get("TO_EMAIL")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, to_email]):
        print("[WARN] SMTP credentials or recipient not fully configured. Skipping e-mail.")
        return

    msg = EmailMessage()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    msg["Subject"] = f"Steam New Games {date_str}"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(f"Attached are the new Steam games detected on {date_str}.")

    with csv_path.open("rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="text", subtype="csv", filename=csv_path.name)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
    print("[INFO] E-mail sent.")

def main():
    logger.info("Starting Steam daily crawler …")
    known_ids = load_known_appids()
    logger.info("Known app count: %s", len(known_ids))

    applist = fetch_full_applist()
    latest_ids = {app["appid"] for app in applist}
    new_ids = latest_ids - known_ids
    if not new_ids:
        logger.info("No new app_ids detected.")
        save_known_appids(latest_ids)
        return

    logger.info("Detected %s new app_ids. Fetching details …", len(new_ids))
    rows = []
    total_fetched = 0
    already_released_filtered = 0
    
    def _task(aid):
        return aid, fetch_app_details(aid)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(_task, aid): aid for aid in new_ids}
        for idx, fut in enumerate(as_completed(futures), start=1):
            total_fetched += 1
            aid, details = fut.result()
            row = build_row(details)
            if not row and details:  # Details exist but filtered by date
                already_released_filtered += 1
            elif row:
                rows.append(row)
            if idx % 100 == 0:
                logger.info("Fetched details for %d/%d apps", idx, len(new_ids))

        logger.info("Filtering summary: %d apps fetched, %d already-released filtered, %d unreleased rows", 
                total_fetched, already_released_filtered, len(rows))

    if rows:
        csv_path = export_csv(rows)
        logger.info("Exported %d rows to %s", len(rows), csv_path)
        send_email(csv_path)
    else:
        logger.warning("No valid app details fetched.")

    # Update stored applist
    save_known_appids(latest_ids)
    logger.info("Finished.")

if __name__ == "__main__":
    # Adjust timezone to America/Los_Angeles if script is run in cron in UTC server.
    os.environ["TZ"] = "America/Los_Angeles"
    try:
        import time
        time.tzset()
    except AttributeError:
        pass
    main() 