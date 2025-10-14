import argparse
import csv
import json
from pathlib import Path
import time
from typing import Iterable, List, Set, Dict, Optional
from datetime import datetime, date
import logging
import requests
from xml.etree import ElementTree as ET
import random

from concurrent.futures import ThreadPoolExecutor, as_completed

# Reuse existing logic and field order from the main crawler
import steam_daily as daily

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def read_applist_ids(path: Path) -> Set[int]:
    """Read a JSON list of app IDs (from KNOWN_APPS_FILE snapshots)."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {int(x) for x in data}


def read_csv_appids(path: Path) -> Set[int]:
    """Read app IDs from a daily CSV export.

    Note: These are only the IDs discovered on that day, not the full Steam applist snapshot.
    """
    appids: Set[int] = set()
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            value = row.get("steam_appid")
            if not value:
                continue
            try:
                appids.add(int(value))
            except ValueError:
                # ignore malformed IDs
                pass
    return appids


def read_csv_appids_dir(dir_path: Path) -> Set[int]:
    """Read app IDs from all CSV files in a directory (non-recursive)."""
    appids: Set[int] = set()
    if not dir_path.exists() or not dir_path.is_dir():
        logger.warning(f"Exclude dir not found or not a directory: {dir_path}")
        return appids
    for csv_path in dir_path.glob("*.csv"):
        try:
            appids |= read_csv_appids(csv_path)
        except Exception as e:
            logger.warning(f"Failed reading CSV for exclude: {csv_path} ({e})")
    return appids


def read_csv_appids_dir_filtered(
    dir_path: Path,
    include_pattern: str = "new_games_*.csv",
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
) -> Set[int]:
    """Read app IDs from CSV files in a directory filtered by filename pattern and date range.

    - include_pattern: glob pattern to select files (default only daily new_games CSVs)
    - start_date_str / end_date_str: YYYY-MM-DD inclusive date range matched from filename
    """
    appids: Set[int] = set()
    if not dir_path.exists() or not dir_path.is_dir():
        logger.warning(f"Source dir not found or not a directory: {dir_path}")
        return appids

    start_dt: Optional[date] = None
    end_dt: Optional[date] = None
    if start_date_str:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    if end_date_str:
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    import re
    date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")

    total_files = 0
    used_files = 0
    for csv_path in dir_path.glob(include_pattern):
        total_files += 1
        fname = csv_path.name
        m = date_re.search(fname)
        if m:
            try:
                fdate = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
            if start_dt and fdate < start_dt:
                continue
            if end_dt and fdate > end_dt:
                continue
        # If no date found in filename, skip to avoid pulling unrelated large CSVs
        else:
            continue

        used_files += 1
        try:
            appids |= read_csv_appids(csv_path)
        except Exception as e:
            logger.warning(f"Failed reading CSV: {csv_path} ({e})")

    logger.info(f"Scanned {total_files} files in {dir_path}, used {used_files} files matching pattern/date range")
    return appids

def fetch_app_details_with_retry(appid: int, session: requests.Session, max_retries: int = 3) -> Dict:
    """Fetch app details with robust retry logic and rate limiting handling."""
    url = daily.DETAILS_URL_TEMPLATE.format(appid=appid)
    
    for attempt in range(max_retries):
        try:
            # Progressive delay: 1s, 2s, 4s for retries
            base_delay = 1.0 + (attempt * 0.5)
            time.sleep(base_delay)
            
            resp = session.get(url, timeout=20)
            
            # Handle rate limiting specifically
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)  # Wait 30s, 60s, 90s
                    logger.warning(f"Rate limited for app {appid}, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Rate limited for app {appid}, max retries exceeded")
                    return {"_api_response": "rate_limited", "_app_id": appid}
            
            resp.raise_for_status()
            data = resp.json().get(str(appid), {})
            
            # Enhanced response handling for early-stage apps
            if not data.get("success"):
                return {"_api_response": "failed", "_app_id": appid}
            
            details = data.get("data", {})
            if details:
                details["_api_response"] = "success"
            return details
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Request failed for app {appid} (attempt {attempt + 1}): {e}, retrying...")
                time.sleep(5)  # Wait 5s before retry for network errors
                continue
            else:
                logger.warning(f"Failed to fetch details for app {appid} after {max_retries} attempts: {e}")
                return {"_api_response": "error", "_app_id": appid, "_error": str(e)}
        except Exception as e:
            logger.warning(f"Unexpected error for app {appid}: {e}")
            return {"_api_response": "error", "_app_id": appid, "_error": str(e)}
    
    return {"_api_response": "error", "_app_id": appid}

def fetch_follower_count_with_retry(appid: int, session: requests.Session, max_retries: int = 2) -> Optional[int]:
    """Fetch Steam community followers with better error handling for XML parsing."""
    headers = {
        "User-Agent": "Mozilla/5.0 (FollowerBot/1.0)",
        "Cookie": "birthtime=0"   # 绕过年龄墙
    }
    
    for attempt in range(max_retries):
        try:
            # Add jitter to avoid thundering herd
            jitter = random.uniform(0.1, 0.5)
            time.sleep(0.5 + jitter)
            
            resp = session.get(daily.FOLLOWER_URL.format(appid=appid), headers=headers, timeout=15)
            
            # Handle rate limiting
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    logger.warning(f"Follower rate limited for app {appid}, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Follower rate limited for app {appid}, max retries exceeded")
                    return None
            
            resp.raise_for_status()
            
            # Simple XML parsing like steam_daily.py, but with retry logic
            try:
                xml_root = ET.fromstring(resp.text)
                member_tag = xml_root.find("./groupDetails/memberCount")
                return int(member_tag.text) if member_tag is not None else None
            except Exception as e:
                logger.warning(f"Follower fetch failed for {appid}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None
                
        except requests.exceptions.RequestException as e:
            if "429" in str(e):
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    logger.warning(f"Follower request failed for app {appid} (429), waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
            logger.warning(f"Follower fetch failed for {appid}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Follower fetch failed for {appid}: {e}")
            return None
    
    return None

def fetch_wishlist_rank_with_retry(appid: int, session: requests.Session, max_retries: int = 2) -> Optional[int]:
    """Fetch SteamDB wishlist rank with better error handling for 403s."""
    headers = {
        "User-Agent": "Mozilla/5.0 (SteamDBBot/1.0)"
    }
    
    for attempt in range(max_retries):
        try:
            # Add jitter and longer delay for SteamDB
            jitter = random.uniform(0.2, 0.8)
            time.sleep(1.0 + jitter)
            
            url = daily.STEAMDB_URL.format(appid=appid)
            resp = session.get(url, headers=headers, timeout=15)
            
            # Handle common errors gracefully
            if resp.status_code == 403:
                # SteamDB blocks some apps - this is normal
                return None
            elif resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 60 * (attempt + 1)
                    logger.warning(f"SteamDB rate limited for app {appid}, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return None
            
            resp.raise_for_status()
            m = daily.WISHLIST_RE.search(resp.text)
            return int(m.group(1)) if m else None
            
        except requests.exceptions.RequestException as e:
            if "403" in str(e):
                # 403 is common for SteamDB, don't retry
                return None
            elif "429" in str(e) and attempt < max_retries - 1:
                wait_time = 60 * (attempt + 1)
                logger.warning(f"SteamDB request failed for app {appid} (429), waiting {wait_time}s")
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"Wishlist rank fetch failed for {appid}: {e}")
                return None
        except Exception as e:
            logger.warning(f"Wishlist rank fetch failed for {appid}: {e}")
            return None
    
    return None

def fetch_wishlist_data_improved(appid: int, details: Dict = None, session: requests.Session = None) -> Dict:
    """Improved wishlist data fetching with better error handling."""
    sess = session or requests.Session()
    
    # 获取关注者数 - with better error handling
    followers = fetch_follower_count_with_retry(appid, sess)
    
    # 如果有关注者数据，估算愿望单
    wishlists_est = None
    if followers is not None:
        # 提取游戏类型用于估算
        genres = []
        if details:
            if details.get('genres'):
                # 处理新数据结构
                if isinstance(details['genres'], list) and all(isinstance(g, str) for g in details['genres']):
                    genres = details['genres']
                # 处理旧数据结构
                elif isinstance(details['genres'], list) and all(isinstance(g, dict) for g in details['genres']):
                    genres = [g.get('description', '') for g in details['genres']]
        
        wishlists_est = daily.estimate_wishlists(followers, genres)
    
    # 获取SteamDB排名 - with better error handling and only for popular games
    wishlist_rank = None
    if followers and followers > 100:  # 只有一定关注者的游戏才尝试获取排名
        wishlist_rank = fetch_wishlist_rank_with_retry(appid, sess)
    
    return {
        "followers": followers,
        "wishlists_est": wishlists_est,
        "wishlist_rank": wishlist_rank
    }

def fetch_rows_for_appids(appids: Iterable[int], max_workers: int = 32, delay_seconds: float = 0.0, skip_followers: bool = False) -> List[Dict]:
    """Fetch app details and wishlist data in parallel with improved error handling and rate limiting.

    When skip_followers is True, follower and wishlist ranking lookups are skipped to avoid XML errors and speed up backfill.
    """
    appids_set = list({int(a) for a in appids})
    logger.info(f"Fetching data for {len(appids_set)} apps with {max_workers} workers and {delay_seconds}s delay")

    def _task(appid: int):
        # Create session for this worker
        session = requests.Session()
        
        try:
            # Optional pacing to avoid 429s - with jitter
            if delay_seconds:
                jitter = random.uniform(0, delay_seconds * 0.2)  # Add up to 20% jitter
                time.sleep(delay_seconds + jitter)
            
            # Use improved fetch function with retry logic
            details = fetch_app_details_with_retry(appid, session)
            
            wishlist_data = None
            if not skip_followers and details and details.get("_api_response") == "success" and details.get("name"):
                # Additional delay before wishlist data fetch
                if delay_seconds:
                    jitter = random.uniform(0, delay_seconds * 0.1)
                    time.sleep(delay_seconds + jitter)
                wishlist_data = fetch_wishlist_data_improved(appid, details, session)
            
            return appid, details, wishlist_data
        except Exception as e:
            logger.error(f"Task failed for app {appid}: {e}")
            return appid, {"_api_response": "error", "_app_id": appid, "_error": str(e)}, None
        finally:
            session.close()

    rows: List[Dict] = []
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_task, aid): aid for aid in appids_set}
        
        for future in as_completed(futures):
            try:
                appid, details, wishlist_data = future.result()
                row = daily.build_row(details, appid, wishlist_data)
                if row:
                    rows.append(row)
                
                completed_count += 1
                if completed_count % 50 == 0:  # Progress logging
                    logger.info(f"Completed {completed_count}/{len(appids_set)} apps ({len(rows)} successful)")
                    
            except Exception as e:
                logger.error(f"Failed to process future result: {e}")
    
    logger.info(f"Finished processing all apps. Generated {len(rows)} rows from {len(appids_set)} apps")
    return rows


def write_csv(rows: List[Dict], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=daily.FIELDS)
        writer.writeheader()
        for row in rows:
            cleaned_row: Dict[str, Optional[str]] = {}
            for key, value in row.items():
                if isinstance(value, str) and value:
                    if key in [
                        "name",
                        "description",
                        "developers",
                        "publishers",
                        "categories",
                        "genres",
                    ]:
                        cleaned_row[key] = daily.clean_text_content(value)
                    else:
                        cleaned_row[key] = value
                else:
                    cleaned_row[key] = value
            writer.writerow(cleaned_row)
    return output


def main():
    parser = argparse.ArgumentParser(description="Backfill generator for missed Steam crawler days")
    group = parser.add_mutually_exclusive_group(required=True)

    # Preferred mode: supply two applist snapshots to find truly new app IDs
    group.add_argument(
        "--diff-applists",
        nargs=2,
        metavar=("OLD_APPLIST.json", "NEW_APPLIST.json"),
        help="Diff two applist.json snapshots to find new app IDs",
    )

    # Fallback mode: derive IDs from a later daily CSV (cannot separate exact days!)
    group.add_argument(
        "--from-csv",
        metavar="LATER_DAILY_CSV",
        help="Generate rows for app IDs listed in a later daily CSV (best-effort)",
    )
    group.add_argument(
        "--from-csv-dir",
        metavar="DAILY_CSV_DIR",
        help="Generate rows from CSVs in a directory, optionally filter by date range",
    )

    parser.add_argument(
        "--exclude-csv",
        metavar="EARLIER_DAILY_CSV",
        help="Optional: exclude app IDs present in an earlier daily CSV (may be disjoint)",
    )
    parser.add_argument(
        "--exclude-csv-dir",
        metavar="EXCLUDE_CSV_DIR",
        help="Optional: exclude app IDs present in ALL CSV files within this directory (non-recursive)",
    )
    parser.add_argument(
        "--exclude-start",
        metavar="YYYY-MM-DD",
        help="Optional: start date (inclusive) for filtering exclude dir (only applies with --exclude-csv-dir)",
    )
    parser.add_argument(
        "--exclude-end",
        metavar="YYYY-MM-DD",
        help="Optional: end date (inclusive) for filtering exclude dir (only applies with --exclude-csv-dir)",
    )
    parser.add_argument(
        "--from-start",
        metavar="YYYY-MM-DD",
        help="Optional: start date (inclusive) for --from-csv-dir filtering",
    )
    parser.add_argument(
        "--from-end",
        metavar="YYYY-MM-DD",
        help="Optional: end date (inclusive) for --from-csv-dir filtering",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path (e.g., exports/backfill_2025-08-19_to_2025-08-20.csv)",
    )
    parser.add_argument("--max-workers", type=int, default=8, help="Number of concurrent workers (reduced from daily default for backfill)")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="Per-request delay (seconds) to avoid 429 rate limits during backfill (increased from daily default)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to see detailed error information for XML parsing issues",
    )
    parser.add_argument(
        "--skip-followers",
        action="store_true",
        help="Skip follower and wishlist lookups to avoid XML errors and speed up backfill",
    )

    args = parser.parse_args()
    output_path = Path(args.output)
    
    # Set debug logging level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

    # Compute target app IDs
    target_appids: Set[int]

    if args.diff_applists:
        old_path = Path(args.diff_applists[0])
        new_path = Path(args.diff_applists[1])
        old_ids = read_applist_ids(old_path)
        new_ids = read_applist_ids(new_path)
        target_appids = new_ids - old_ids
    elif args.from_csv_dir:
        src_dir = Path(args.from_csv_dir)
        target_appids = read_csv_appids_dir_filtered(src_dir, include_pattern="new_games_*.csv", start_date_str=args.from_start, end_date_str=args.from_end)
    else:
        later_csv_path = Path(args.from_csv)
        target_appids = read_csv_appids(later_csv_path)
        if args.exclude_csv:
            earlier_csv_ids = read_csv_appids(Path(args.exclude_csv))
            target_appids = target_appids - earlier_csv_ids
        if args.exclude_csv_dir:
            # If exclude date range provided, filter exclude dir as well using the same pattern
            if args.exclude_start or args.exclude_end:
                dir_ids = read_csv_appids_dir_filtered(Path(args.exclude_csv_dir), include_pattern="new_games_*.csv", start_date_str=args.exclude_start, end_date_str=args.exclude_end)
                logger.info(f"Collected {len(dir_ids)} app IDs from exclude dir (filtered by date) {args.exclude_csv_dir}")
            else:
                dir_ids = read_csv_appids_dir(Path(args.exclude_csv_dir))
                logger.info(f"Collected {len(dir_ids)} app IDs from exclude dir {args.exclude_csv_dir}")
            target_appids = target_appids - dir_ids

    if not target_appids:
        logger.info("No target app IDs found for backfill. Nothing to do.")
        return

    logger.info(f"Found {len(target_appids)} target app IDs for backfill")
    # Sanity hints if count looks suspiciously high
    if len(target_appids) > 2000:
        logger.warning("Target app IDs exceed 2000. Did you pass a multi-day CSV or the full applist?")
        logger.warning("Consider using --diff-applists for two specific snapshots or providing a single-day CSV plus --exclude-csv of the prior day.")
    logger.info(f"Configuration: {args.max_workers} workers, {args.delay}s delay per request")
    if args.skip_followers:
        logger.info("Skip followers mode is ON: will not fetch followers / wishlist rank")
    
    # Estimate time based on configuration
    estimated_time_minutes = (len(target_appids) * args.delay * 2) / (args.max_workers * 60)  # rough estimate
    logger.info(f"Estimated processing time: {estimated_time_minutes:.1f} minutes")

    # Fetch details and build rows
    start_time = time.time()
    rows = fetch_rows_for_appids(
        sorted(target_appids),
        max_workers=args.max_workers,
        delay_seconds=args.delay,
        skip_followers=args.skip_followers,
    )
    
    elapsed_time = time.time() - start_time
    logger.info(f"Processing completed in {elapsed_time/60:.1f} minutes")
    
    if not rows:
        logger.warning("No rows produced (all filtered or fetch failures).")
        return

    # Write output CSV using consistent field order and cleaning
    write_csv(rows, output_path)
    success_rate = (len(rows) / len(target_appids)) * 100
    logger.info(f"Backfill CSV written: {output_path}")
    logger.info(f"Results: {len(rows)} successful rows from {len(target_appids)} target apps ({success_rate:.1f}% success rate)")


if __name__ == "__main__":
    main()


