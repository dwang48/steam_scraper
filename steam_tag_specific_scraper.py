#!/usr/bin/env python3
"""
Steam标签分类爬虫
分别爬取不同类型的标签：narrative, emotional, co-op, cozy
每种标签类型单独处理和导出
"""

import os
import json
import csv
import requests
import logging
import time
import html
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Constants
APPLIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
DETAILS_URL_TEMPLATE = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"

# 分别定义每种标签类型
TAG_CATEGORIES = {
    "narrative": {
        "tags": ["Story Rich", "Narrative", "Choose Your Own Adventure", "Interactive Fiction", "Visual Novel", "Text-Based"],
        "description": "叙事类游戏"
    },
    "emotional": {
        "tags": ["Emotional", "Psychological", "Drama", "Atmospheric", "Meaningful Choices", "Character Development"],
        "description": "情感类游戏"
    },
    "co-op": {
        "tags": ["Co-op", "Local Co-Op", "Online Co-Op", "Cooperative", "Multiplayer", "Local Multiplayer"],
        "description": "合作类游戏"
    },
    "cozy": {
        "tags": ["Cozy", "Relaxing", "Casual", "Peaceful", "Zen", "Wholesome", "Family Friendly"],
        "description": "温馨休闲游戏"
    }
}

# 输出字段
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
    "target_tags_found",
    "tag_category",  # 新增：标签类型
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
logger = logging.getLogger("steam_tag_specific")

def fetch_full_applist() -> List[Dict]:
    """Download the full Steam app list."""
    logger.info("获取Steam应用列表...")
    resp = requests.get(APPLIST_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    apps = data.get("applist", {}).get("apps", [])
    logger.info(f"找到 {len(apps)} 个应用")
    return apps

def fetch_app_details(appid: int, session: requests.Session = None) -> Optional[Dict]:
    """Fetch detailed information for a specific app with improved error handling."""
    sess = session or requests.Session()
    
    # Set browser-like headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    url = DETAILS_URL_TEMPLATE.format(appid=appid)
    
    try:
        # Add delay to be respectful
        time.sleep(1.5)
        
        resp = sess.get(url, headers=headers, timeout=15)
        
        # Skip forbidden apps (they might be region-locked or private)
        if resp.status_code == 403:
            return None
            
        # Handle rate limiting
        if resp.status_code == 429:
            logger.warning(f"速率限制 {appid}，等待30秒...")
            time.sleep(30)
            return None
        
        resp.raise_for_status()
        data = resp.json().get(str(appid), {})
        
        if not data.get("success"):
            return None
        
        details = data.get("data", {})
        return details if details else None
        
    except Exception as e:
        # Only log unexpected errors, not common ones
        if "429" not in str(e) and "403" not in str(e):
            logger.warning(f"应用 {appid} 获取失败: {e}")
        return None

def clean_text_content(text: str) -> str:
    """Clean HTML content and normalize whitespace."""
    if not text:
        return ""
    
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
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
    
    return all_tags

def check_target_tags(available_tags: List[str], target_category: str) -> List[str]:
    """Check which target tags are present for a specific category."""
    found_tags = []
    available_lower = [tag.lower() for tag in available_tags]
    target_tags = TAG_CATEGORIES[target_category]["tags"]
    
    for target_tag in target_tags:
        target_lower = target_tag.lower()
        
        for available_tag in available_lower:
            if target_lower in available_tag or available_tag in target_lower:
                if target_tag not in found_tags:
                    found_tags.append(target_tag)
                break
    
    return found_tags

def is_unreleased_game(details: Dict) -> bool:
    """Check if the game is unreleased."""
    if details.get('type') != 'game':
        return False
    
    release_info = details.get('release_date', {})
    
    if release_info.get('coming_soon') is True:
        return True
    
    if release_info.get('coming_soon') is False:
        return False
    
    # Check for future dates
    release_date = release_info.get('date', '')
    if release_date:
        try:
            from dateutil import parser as dateparser
            parsed_date = dateparser.parse(release_date)
            return parsed_date > datetime.now()
        except:
            pass
    
    return True

def process_app_for_category(appid: int, session: requests.Session, target_category: str) -> Optional[Dict]:
    """Process a single app for a specific tag category."""
    details = fetch_app_details(appid, session)
    
    if not details:
        return None
    
    if not is_unreleased_game(details):
        return None
    
    available_tags = extract_tags_from_details(details)
    found_target_tags = check_target_tags(available_tags, target_category)
    
    if not found_target_tags:
        return None
    
    # Extract detailed information
    release_info = details.get('release_date', {})
    release_date = release_info.get('date', 'TBA')
    coming_soon = release_info.get('coming_soon', True)
    
    description = ""
    if details.get('short_description'):
        description = clean_text_content(details.get('short_description'))
    elif details.get('detailed_description'):
        detailed_desc = details.get('detailed_description', '')
        clean_desc = clean_text_content(detailed_desc)
        description = clean_desc[:300] + '...' if len(clean_desc) > 300 else clean_desc
    
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
        "tag_category": target_category,
        "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }

def search_category(app_batch: List[int], target_category: str, max_finds: int = 1) -> List[Dict]:
    """Search for games in a specific category."""
    results = []
    session = requests.Session()
    
    category_info = TAG_CATEGORIES[target_category]
    logger.info(f"正在搜索 {category_info['description']} 类游戏...")
    logger.info(f"目标标签: {', '.join(category_info['tags'])}")
    
    for i, appid in enumerate(app_batch):
        if len(results) >= max_finds:
            logger.info(f"已找到 {max_finds} 个 {category_info['description']} 游戏，停止搜索")
            break
            
        try:
            result = process_app_for_category(appid, session, target_category)
            if result:
                results.append(result)
                logger.info(f"✓ 找到 {category_info['description']}: {result['name']} (标签: {result['target_tags_found']})")
        
        except KeyboardInterrupt:
            logger.info("用户中断...")
            break
        except Exception as e:
            pass  # Skip errors silently
        
        # Progress update
        if (i + 1) % 100 == 0:
            logger.info(f"  {category_info['description']} 搜索进度: {i + 1}/{len(app_batch)}，已找到 {len(results)} 个")
    
    session.close()
    return results

def export_category_results(results: List[Dict], category: str) -> Path:
    """Export results for a specific category."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = EXPORT_DIR / f"steam_{category}_games_{today_str}.csv"
    
    with file_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in results:
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
    parser = argparse.ArgumentParser(
        description="Steam标签分类爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
标签类型:
  narrative  - 叙事类游戏 (Story Rich, Narrative, Visual Novel等)
  emotional  - 情感类游戏 (Emotional, Psychological, Drama等)
  co-op      - 合作类游戏 (Co-op, Local Co-Op, Online Co-Op等)
  cozy       - 温馨休闲游戏 (Cozy, Relaxing, Casual等)

示例用法:
  python steam_tag_specific_scraper.py --all --limit 1000
  python steam_tag_specific_scraper.py --category narrative --limit 500
  python steam_tag_specific_scraper.py --category co-op --max-finds 3
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all", 
        action="store_true",
        help="搜索所有四种类型的游戏"
    )
    group.add_argument(
        "--category",
        choices=list(TAG_CATEGORIES.keys()),
        help="搜索特定类型的游戏"
    )
    
    parser.add_argument(
        "--limit", 
        type=int, 
        default=1000,
        help="限制搜索的应用数量（默认1000）"
    )
    
    parser.add_argument(
        "--max-finds", 
        type=int, 
        default=1,
        help="每种类型最多找到多少个游戏（默认1个）"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Steam标签分类爬虫启动")
    logger.info("="*60)
    
    # Get app list
    all_apps = fetch_full_applist()
    sorted_apps = sorted(all_apps, key=lambda x: x['appid'], reverse=True)
    limited_apps = [app['appid'] for app in sorted_apps[:args.limit]]
    
    logger.info(f"将在最新 {len(limited_apps)} 个应用中搜索")
    
    if args.all:
        # Search all categories
        all_results = {}
        for category in TAG_CATEGORIES.keys():
            logger.info(f"\n{'='*40}")
            results = search_category(limited_apps, category, args.max_finds)
            all_results[category] = results
            
            if results:
                csv_path = export_category_results(results, category)
                logger.info(f"✅ {TAG_CATEGORIES[category]['description']} 结果已导出: {csv_path}")
            else:
                logger.info(f"❌ 未找到 {TAG_CATEGORIES[category]['description']} 游戏")
        
        # Print summary
        print(f"\n{'='*60}")
        print("搜索总结:")
        for category, results in all_results.items():
            print(f"- {TAG_CATEGORIES[category]['description']}: {len(results)} 个游戏")
            for result in results:
                print(f"  • {result['name']} ({result['target_tags_found']})")
    
    else:
        # Search single category
        results = search_category(limited_apps, args.category, args.max_finds)
        
        if results:
            csv_path = export_category_results(results, args.category)
            logger.info(f"✅ 找到 {len(results)} 个 {TAG_CATEGORIES[args.category]['description']} 游戏")
            logger.info(f"结果已导出: {csv_path}")
            
            print(f"\n{'='*60}")
            print(f"发现的 {TAG_CATEGORIES[args.category]['description']}:")
            for result in results:
                print(f"- {result['name']}")
                print(f"  标签: {result['target_tags_found']}")
                print(f"  发布日期: {result['release_date']}")
                print(f"  Steam链接: {result['steam_url']}")
                print()
        else:
            logger.info(f"未找到 {TAG_CATEGORIES[args.category]['description']} 游戏")
    
    logger.info("搜索完成！")

if __name__ == "__main__":
    main()
