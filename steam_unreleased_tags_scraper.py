import os
import json
import csv
import requests
import logging
import time
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Constants
APPLIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
DETAILS_URL_TEMPLATE = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
SEARCH_URL = "https://store.steampowered.com/search/results"

# Target tags for searching
TARGET_TAGS = {
    "co-op": ["Co-op", "Local Co-Op", "Online Co-Op", "Cooperative"],
    "emotional": ["Emotional", "Story Rich", "Psychological", "Drama"],
    "narrative": ["Story Rich", "Narrative", "Choose Your Own Adventure", "Interactive Fiction"]
}

# Flattened list of all tags we're interested in
ALL_TARGET_TAGS = []
for tag_group in TARGET_TAGS.values():
    ALL_TARGET_TAGS.extend(tag_group)

# Output fields
FIELDS = [
    "name",
    "steam_appid", 
    "steam_url",
    "developers",
    "publishers",
    "categories",
    "genres",
    "tags",
    "release_date",
    "coming_soon",
    "description",
    "supported_languages",
    "website",
    "target_tags_found",  # Which of our target tags were found
    "discovery_date"
]

# Setup directories
DATA_DIR = Path(__file__).parent / "steam_data"
EXPORT_DIR = Path(__file__).parent / "exports"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("steam_unreleased_tags")

MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "4"))  # Very conservative to avoid rate limiting

def fetch_full_applist() -> List[Dict]:
    """Download the full Steam app list."""
    logger.info("Fetching Steam app list...")
    resp = requests.get(APPLIST_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    apps = data.get("applist", {}).get("apps", [])
    logger.info(f"Found {len(apps)} apps in Steam database")
    return apps

def fetch_app_details(appid: int, session: requests.Session = None) -> Optional[Dict]:
    """Fetch detailed information for a specific app with retry mechanism."""
    sess = session or requests.Session()
    
    # Set browser-like headers to avoid blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    url = DETAILS_URL_TEMPLATE.format(appid=appid)
    
    max_retries = 3
    base_delay = 1.0  # Increased base delay
    
    for attempt in range(max_retries):
        try:
            # Progressive delay: 1s, 2s, 4s for retries
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
            
            resp = sess.get(url, headers=headers, timeout=15)
            
            # Handle rate limiting specifically
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)  # Wait 30s, 60s, 90s
                    logger.warning(f"Rate limited for app {appid}, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Rate limited for app {appid}, max retries exceeded")
                    return None
            
            resp.raise_for_status()
            data = resp.json().get(str(appid), {})
            
            if not data.get("success"):
                return None
            
            details = data.get("data", {})
            return details if details else None
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Request failed for app {appid} (attempt {attempt + 1}): {e}, retrying...")
                time.sleep(5)  # Wait 5s before retry for network errors
                continue
            else:
                logger.warning(f"Failed to fetch details for app {appid} after {max_retries} attempts: {e}")
                return None
        except Exception as e:
            logger.warning(f"Unexpected error for app {appid}: {e}")
            return None
    
    return None

def clean_text_content(text: str) -> str:
    """Clean HTML content and normalize whitespace."""
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_tags_from_details(details: Dict) -> List[str]:
    """Extract all available tags/categories from game details."""
    all_tags = []
    
    # Extract from categories
    if details.get('categories'):
        for cat in details['categories']:
            if isinstance(cat, dict) and cat.get('description'):
                all_tags.append(cat['description'])
    
    # Extract from genres
    if details.get('genres'):
        for genre in details['genres']:
            if isinstance(genre, dict) and genre.get('description'):
                all_tags.append(genre['description'])
    
    # Note: Steam's API doesn't directly provide user tags
    # but categories and genres often overlap with popular tags
    
    return all_tags

def check_target_tags(available_tags: List[str]) -> List[str]:
    """Check which target tags are present in the available tags."""
    found_tags = []
    available_lower = [tag.lower() for tag in available_tags]
    
    for target_tag in ALL_TARGET_TAGS:
        target_lower = target_tag.lower()
        
        # Check for exact matches or partial matches
        for available_tag in available_lower:
            if target_lower in available_tag or available_tag in target_lower:
                if target_tag not in found_tags:
                    found_tags.append(target_tag)
                break
    
    return found_tags

def is_unreleased_game(details: Dict) -> bool:
    """Check if the game is unreleased and is actually a game."""
    # Must be a game
    if details.get('type') != 'game':
        return False
    
    # Check release status
    release_info = details.get('release_date', {})
    
    # If coming_soon is explicitly True, it's unreleased
    if release_info.get('coming_soon') is True:
        return True
    
    # If coming_soon is False, it's released
    if release_info.get('coming_soon') is False:
        return False
    
    # If no clear coming_soon info, check if there's a future date
    release_date = release_info.get('date', '')
    if release_date:
        try:
            # Try to parse the date and see if it's in the future
            from dateutil import parser as dateparser
            parsed_date = dateparser.parse(release_date)
            return parsed_date > datetime.now()
        except:
            pass
    
    # Default to treating as potentially unreleased if unclear
    return True

def process_app(appid: int, session: requests.Session) -> Optional[Dict]:
    """Process a single app and return formatted data if it matches criteria."""
    details = fetch_app_details(appid, session)
    
    if not details:
        return None
    
    # Check if it's an unreleased game
    if not is_unreleased_game(details):
        return None
    
    # Extract available tags
    available_tags = extract_tags_from_details(details)
    
    # Check for target tags
    found_target_tags = check_target_tags(available_tags)
    
    # Only include games that have at least one target tag
    if not found_target_tags:
        return None
    
    # Extract release date info
    release_info = details.get('release_date', {})
    release_date = release_info.get('date', 'TBA')
    coming_soon = release_info.get('coming_soon', True)
    
    # Extract description
    description = ""
    if details.get('short_description'):
        description = clean_text_content(details.get('short_description'))
    elif details.get('detailed_description'):
        detailed_desc = details.get('detailed_description', '')
        clean_desc = clean_text_content(detailed_desc)
        description = clean_desc[:300] + '...' if len(clean_desc) > 300 else clean_desc
    
    # Extract supported languages
    supported_languages = []
    if details.get('supported_languages'):
        lang_text = details.get('supported_languages', '')
        languages = re.findall(r'>([^<]+)<', lang_text)
        if not languages:
            languages = [lang.strip() for lang in lang_text.split(',')]
        supported_languages = [lang.strip() for lang in languages if lang.strip()]
    
    return {
        "name": details.get('name', ''),
        "steam_appid": str(appid),
        "steam_url": f"https://store.steampowered.com/app/{appid}/",
        "developers": ";".join(details.get('developers', [])) if details.get('developers') else None,
        "publishers": ";".join(details.get('publishers', [])) if details.get('publishers') else None,
        "categories": ";".join([cat.get('description', '') for cat in details.get('categories', [])]) if details.get('categories') else None,
        "genres": ";".join([genre.get('description', '') for genre in details.get('genres', [])]) if details.get('genres') else None,
        "tags": ";".join(available_tags) if available_tags else None,
        "release_date": release_date,
        "coming_soon": coming_soon,
        "description": description,
        "supported_languages": ";".join(supported_languages) if supported_languages else None,
        "website": details.get('website'),
        "target_tags_found": ";".join(found_target_tags),
        "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }

def search_by_batch(app_batch: List[int], batch_num: int, total_batches: int) -> List[Dict]:
    """Process a batch of apps."""
    results = []
    session = requests.Session()
    
    logger.info(f"Processing batch {batch_num}/{total_batches} with {len(app_batch)} apps...")
    
    for i, appid in enumerate(app_batch):
        try:
            result = process_app(appid, session)
            if result:
                results.append(result)
                logger.info(f"✓ Found match: {result['name']} (tags: {result['target_tags_found']})")
        except Exception as e:
            logger.warning(f"Error processing app {appid}: {e}")
        
        # Progress update every 50 apps
        if (i + 1) % 50 == 0:
            logger.info(f"  Batch {batch_num} progress: {i + 1}/{len(app_batch)} apps processed")
    
    session.close()
    return results

def export_results(results: List[Dict]) -> Path:
    """Export results to CSV file."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = EXPORT_DIR / f"steam_unreleased_tags_{today_str}.csv"
    
    with file_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in results:
            # Clean text fields
            cleaned_row = {}
            for key, value in row.items():
                if isinstance(value, str) and value:
                    if key in ['name', 'description', 'developers', 'publishers']:
                        cleaned_row[key] = clean_text_content(value)
                    else:
                        cleaned_row[key] = value
                else:
                    cleaned_row[key] = value
            writer.writerow(cleaned_row)
    
    return file_path

def main():
    """Main execution function."""
    logger.info("Starting Steam unreleased games with target tags scraper...")
    logger.info(f"Target tags: {', '.join(ALL_TARGET_TAGS)}")
    
    # Get all Steam apps
    all_apps = fetch_full_applist()
    
    # Filter out obvious non-games (some basic filtering by name patterns)
    filtered_apps = []
    for app in all_apps:
        name = app.get('name', '').lower()
        # Skip obvious non-games
        if any(skip_word in name for skip_word in ['soundtrack', 'wallpaper', 'server', 'tool', 'sdk']):
            continue
        filtered_apps.append(app['appid'])
    
    logger.info(f"Filtered to {len(filtered_apps)} potential games from {len(all_apps)} total apps")
    
    # Split into batches for processing
    batch_size = 500  # Process in smaller batches
    batches = [filtered_apps[i:i + batch_size] for i in range(0, len(filtered_apps), batch_size)]
    
    logger.info(f"Processing {len(batches)} batches of up to {batch_size} apps each...")
    
    all_results = []
    
    # Process batches with very limited concurrency to avoid rate limiting
    with ThreadPoolExecutor(max_workers=2) as executor:  # Very conservative thread count
        future_to_batch = {
            executor.submit(search_by_batch, batch, i + 1, len(batches)): i 
            for i, batch in enumerate(batches)
        }
        
        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                logger.info(f"Batch {batch_idx + 1} completed. Found {len(batch_results)} matches. Total so far: {len(all_results)}")
            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} failed: {e}")
    
    # Export results
    if all_results:
        csv_path = export_results(all_results)
        logger.info(f"✅ Found {len(all_results)} unreleased games with target tags!")
        logger.info(f"Results exported to: {csv_path}")
        
        # Print summary by tag type
        tag_summary = {}
        for result in all_results:
            found_tags = result.get('target_tags_found', '').split(';')
            for tag in found_tags:
                if tag:
                    tag_summary[tag] = tag_summary.get(tag, 0) + 1
        
        logger.info("\nSummary by tag:")
        for tag, count in sorted(tag_summary.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {tag}: {count} games")
    else:
        logger.info("No unreleased games found with the target tags.")
    
    logger.info("Scraping completed!")

if __name__ == "__main__":
    main()
