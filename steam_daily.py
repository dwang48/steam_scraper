import os
import json
import csv
import smtplib
import tempfile
import argparse
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
WATCHLIST_FILE = DATA_DIR / "early_stage_watchlist.json"  # New file for tracking early-stage apps

# Updated fields to include early-stage app detection
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
    "detection_stage",  # New field: "public_unreleased", "early_stage", "minimal_data"
    "api_response_type",  # New field: "full_details", "minimal_data", "no_response"
    "discovery_date"     # New field: when we first detected this app
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

def load_watchlist() -> Dict:
    """Load the early-stage app watchlist"""
    if WATCHLIST_FILE.exists():
        with WATCHLIST_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_watchlist(watchlist: Dict):
    """Save the early-stage app watchlist"""
    with WATCHLIST_FILE.open("w", encoding="utf-8") as f:
        json.dump(watchlist, f, indent=2)

def update_watchlist_entry(watchlist: Dict, app_id: int, status: str, details: Dict = None) -> Dict:
    """Update or create a watchlist entry"""
    app_id_str = str(app_id)
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if app_id_str not in watchlist:
        # New entry
        watchlist[app_id_str] = {
            "first_detected": current_date,
            "last_checked": current_date,
            "status_history": [{"date": current_date, "status": status}],
            "check_count": 1,
            "current_status": status
        }
    else:
        # Update existing entry
        entry = watchlist[app_id_str]
        entry["last_checked"] = current_date
        entry["check_count"] = entry.get("check_count", 0) + 1
        
        # Add to history if status changed
        if entry.get("current_status") != status:
            entry["status_history"].append({"date": current_date, "status": status})
            entry["current_status"] = status
    
    # Add current details if available
    if details and details.get("name"):
        watchlist[app_id_str]["latest_name"] = details["name"]
        watchlist[app_id_str]["latest_type"] = details.get("type", "unknown")
    
    return watchlist

def fetch_app_details(appid: int) -> Dict:
    url = DETAILS_URL_TEMPLATE.format(appid=appid)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json().get(str(appid), {})
        
        # Enhanced response handling for early-stage apps
        if not data.get("success"):
            # Even failed API calls can give us valuable info about early apps
            return {"_api_response": "failed", "_app_id": appid}
        
        details = data.get("data", {})
        if details:
            details["_api_response"] = "success"
        return details
    except Exception as e:
        # Capture network/parsing errors too
        return {"_api_response": "error", "_app_id": appid, "_error": str(e)}

def build_row(details: Dict, app_id: int = None) -> Dict:
    """Enhanced to capture early-stage apps with minimal data"""
    discovery_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Handle apps with no API response or minimal data
    if not details or details.get("_api_response") in ["failed", "error"]:
        return {
            "type": "unknown",
            "name": f"Early Stage App (ID: {app_id or details.get('_app_id', 'unknown')})",
            "steam_appid": str(app_id or details.get("_app_id", "")),
            "developers": None,
            "publishers": None,
            "header_image": None,
            "website": None,
            "categories": None,
            "genres": None,
            "steam_url": f"https://store.steampowered.com/app/{app_id or details.get('_app_id', '')}" if app_id or details.get('_app_id') else None,
            "detection_stage": "early_stage",
            "api_response_type": details.get("_api_response", "no_response"),
            "discovery_date": discovery_date
        }
    
    # Handle apps with full details
    name = details.get("name")
    if name:
        # Check if it's a released game we should skip
        release_info = details.get("release_date", {})
        if release_info.get("coming_soon") is False:  # Explicitly released
            return {}  # Skip clearly released games
        
        # Include unreleased games with full store pages
        detection_stage = "public_unreleased" if release_info.get("coming_soon") else "minimal_data"
    else:
        # Apps without names are likely very early stage
        detection_stage = "minimal_data"
        name = f"Unnamed App (ID: {details.get('steam_appid', app_id or 'unknown')})"
    
    return {
        "type": details.get("type", "unknown"),
        "name": name,
        "steam_appid": str(details.get("steam_appid", app_id or "")),
        "developers": ";".join(details.get("developers", [])) if details.get("developers") else None,
        "publishers": ";".join(details.get("publishers", [])) if details.get("publishers") else None,
        "header_image": details.get("header_image"),
        "website": details.get("website"),
        "categories": ";".join(c.get("description") for c in details.get("categories", [])) if details.get("categories") else None,
        "genres": ";".join(g.get("description") for g in details.get("genres", [])) if details.get("genres") else None,
        "steam_url": f"https://store.steampowered.com/app/{details.get('steam_appid', app_id or '')}" if details.get('steam_appid') or app_id else None,
        "detection_stage": detection_stage,
        "api_response_type": "full_details",
        "discovery_date": discovery_date
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
    to_emails = os.environ.get("TO_EMAIL")  # Can be single email or comma-separated list
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, to_emails]):
        print("[WARN] SMTP credentials or recipient not fully configured. Skipping e-mail.")
        return

    # Parse email list (support both single email and comma-separated list)
    email_list = [email.strip() for email in to_emails.split(",")]
    logger.info("Sending email to %d recipients", len(email_list))
    
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Read CSV data once
    with csv_path.open("rb") as f:
        csv_data = f.read()
    
    # Send emails with rate limiting
    successful_sends = 0
    failed_sends = 0
    
    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_pass)
        
        for i, to_email in enumerate(email_list):
            try:
                msg = EmailMessage()
                msg["Subject"] = f"Steam New Apps Discovery {date_str}"
                msg["From"] = from_email
                msg["To"] = to_email
                
                # Count different stages for email content
                with open(csv_path, 'r', encoding='utf-8') as f:
                    import csv as csv_module
                    reader = csv_module.DictReader(f)
                    rows_data = list(reader)
                
                early_stage = sum(1 for row in rows_data if row.get('detection_stage') == 'early_stage')
                public_unreleased = sum(1 for row in rows_data if row.get('detection_stage') == 'public_unreleased') 
                minimal_data = sum(1 for row in rows_data if row.get('detection_stage') == 'minimal_data')
                
                email_body = f"""New Steam app discoveries for {date_str}:

📊 Discovery Summary:
• Early-stage apps (no public pages): {early_stage}
• Public unreleased games: {public_unreleased}  
• Minimal data apps: {minimal_data}
• Total discoveries: {len(rows_data)}

"""
                msg.set_content(email_body)
                
                msg.add_attachment(csv_data, maintype="text", subtype="csv", filename=csv_path.name)
                
                smtp.send_message(msg)
                successful_sends += 1
                logger.info("Email sent successfully to %s (%d/%d)", to_email, i+1, len(email_list))
                
                # Rate limiting: pause between emails to avoid spam detection
                if i < len(email_list) - 1 and len(email_list) > 1:
                    import time
                    time.sleep(2)  # 2 second delay between emails
                    
            except Exception as e:
                failed_sends += 1
                logger.error("Failed to send email to %s: %s", to_email, e)
    
    logger.info("Email sending complete: %d successful, %d failed", successful_sends, failed_sends)

def create_test_csv() -> Path:
    """Create a test CSV file for email testing"""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = EXPORT_DIR / f"test_new_games_{today_str}.csv"
    
    # Create test data with different discovery stages
    test_data = [
        {
            "type": "game",
            "name": "Public Unreleased Game",
            "steam_appid": "999999",
            "developers": "Known Developer",
            "publishers": "Known Publisher", 
            "header_image": "https://example.com/test.jpg",
            "website": "https://example.com",
            "categories": "Action;Adventure",
            "genres": "RPG;Simulation",
            "steam_url": "https://store.steampowered.com/app/999999",
            "detection_stage": "public_unreleased",
            "api_response_type": "full_details",
            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        },
        {
            "type": "unknown", 
            "name": "Early Stage App (ID: 999998)",
            "steam_appid": "999998",
            "developers": None,
            "publishers": None,
            "header_image": None, 
            "website": None,
            "categories": None,
            "genres": None,
            "steam_url": "https://store.steampowered.com/app/999998",
            "detection_stage": "early_stage",
            "api_response_type": "failed",
            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        },
        {
            "type": "game",
            "name": "Minimal Data Game",
            "steam_appid": "999997",
            "developers": None,
            "publishers": None,
            "header_image": None,
            "website": None,
            "categories": None,
            "genres": None,
            "steam_url": "https://store.steampowered.com/app/999997",
            "detection_stage": "minimal_data",
            "api_response_type": "full_details",
            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
    ]
    
    with file_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in test_data:
            writer.writerow(row)
    
    return file_path

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Steam daily crawler")
    parser.add_argument("--test", action="store_true", help="Test mode: create dummy CSV and send test email")
    parser.add_argument("--check-watchlist", action="store_true", help="Also check existing watchlist apps for changes")
    args = parser.parse_args()
    
    if args.test:
        logger.info("Running in TEST MODE - creating dummy CSV and sending test email")
        csv_path = create_test_csv()
        logger.info("Created test CSV: %s", csv_path)
        send_email(csv_path)
        logger.info("Test completed.")
        return

    logger.info("Starting Steam daily crawler …")
    known_ids = load_known_appids()
    watchlist = load_watchlist()
    logger.info("Known app count: %s", len(known_ids))
    logger.info("Watchlist app count: %s", len(watchlist))

    # Step 1: Check existing watchlist apps for changes
    watchlist_promotions = []
    if args.check_watchlist and watchlist:
        logger.info("Checking %d watchlist apps for changes...", len(watchlist))
        
        def _watchlist_task(aid):
            return aid, fetch_app_details(aid)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
            watchlist_futures = {exe.submit(_watchlist_task, int(aid)): aid for aid in watchlist.keys()}
            for fut in as_completed(watchlist_futures):
                aid_str = watchlist_futures[fut]
                aid_int = int(aid_str)
                details = fut.result()[1]
                
                # Determine new status
                if details and details.get("_api_response") == "success" and details.get("name"):
                    # App became accessible!
                    row = build_row(details, aid_int)
                    if row:
                        watchlist_promotions.append((aid_int, details, row))
                        logger.info("🎉 Watchlist app %s became accessible: %s", aid_int, details.get("name"))
                    # Update watchlist entry
                    update_watchlist_entry(watchlist, aid_int, "accessible", details)
                else:
                    # Still inaccessible
                    status = details.get("_api_response", "no_response") if details else "no_response"
                    update_watchlist_entry(watchlist, aid_int, status)
        
        if watchlist_promotions:
            logger.info("Found %d watchlist apps that became accessible", len(watchlist_promotions))

    # Step 2: Process new apps from Steam applist
    applist = fetch_full_applist()
    latest_ids = {app["appid"] for app in applist}
    new_ids = latest_ids - known_ids
    
    if not new_ids and not watchlist_promotions:
        logger.info("No new app_ids detected and no watchlist changes.")
        if args.check_watchlist:
            save_watchlist(watchlist)
        save_known_appids(latest_ids)
        return

    logger.info("Detected %s new app_ids. Fetching details …", len(new_ids))
    rows = []
    total_fetched = 0
    already_released_filtered = 0
    new_to_watchlist = 0
    
    def _task(aid):
        return aid, fetch_app_details(aid)

    early_stage_count = 0
    public_unreleased_count = 0
    minimal_data_count = 0
    
    # Process new apps
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(_task, aid): aid for aid in new_ids}
        for idx, fut in enumerate(as_completed(futures), start=1):
            total_fetched += 1
            aid, details = fut.result()
            row = build_row(details, aid)
            
            if not row and details:  # Details exist but filtered by date (released games)
                already_released_filtered += 1
            elif row:
                stage = row.get("detection_stage", "unknown")
                
                if stage == "early_stage":
                    # Add to watchlist instead of main applist
                    early_stage_count += 1
                    new_to_watchlist += 1
                    status = details.get("_api_response", "no_response") if details else "no_response"
                    update_watchlist_entry(watchlist, aid, status, details)
                    logger.info("Added app %s to watchlist (early stage)", aid)
                else:
                    # Add to regular results
                    rows.append(row)
                    if stage == "public_unreleased":
                        public_unreleased_count += 1
                    elif stage == "minimal_data":
                        minimal_data_count += 1
                        
            if idx % 100 == 0:
                logger.info("Fetched details for %d/%d apps", idx, len(new_ids))

    # Add promoted watchlist apps to results
    for aid_int, details, row in watchlist_promotions:
        rows.append(row)
        # Remove from watchlist and add to known apps
        if str(aid_int) in watchlist:
            del watchlist[str(aid_int)]
        known_ids.add(aid_int)

    logger.info("Discovery summary: %d apps processed, %d released (filtered), %d early-stage (watchlisted), %d public unreleased, %d minimal data", 
            total_fetched, already_released_filtered, early_stage_count, public_unreleased_count, minimal_data_count)
    
    if watchlist_promotions:
        logger.info("Promoted %d apps from watchlist to known apps", len(watchlist_promotions))
    
    if new_to_watchlist:
        logger.info("Added %d new apps to watchlist", new_to_watchlist)

    # Export and email results
    if rows:
        csv_path = export_csv(rows)
        logger.info("Exported %d rows to %s", len(rows), csv_path)
        send_email(csv_path)
    else:
        logger.warning("No accessible app details to export.")

    # Save updated data
    save_watchlist(watchlist)
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