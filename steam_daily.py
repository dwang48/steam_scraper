import os
import json
import csv
import smtplib
import sys
import tempfile
import argparse
import re
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import List, Dict, Set, Optional
import logging
from dateutil import parser as dateparser
from difflib import SequenceMatcher
from xml.etree import ElementTree as ET
import time
import random
import html

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.nsfw import classify_nsfw_from_details

# Constants
LEGACY_APPLIST_URLS = [
    "https://api.steampowered.com/ISteamApps/GetAppList/v2/",
    "https://api.steampowered.com/ISteamApps/GetAppList/v0002/?format=json",
]
STORE_APP_LIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
DETAILS_URL_TEMPLATE = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
STORE_PAGE_URL_TEMPLATE = "https://store.steampowered.com/app/{appid}/?cc=us&l=en"
FOLLOWER_URL = "https://steamcommunity.com/games/{appid}/memberslistxml/?xml=1"
STEAMDB_URL = "https://steamdb.info/app/{appid}/"
DATA_DIR = Path(__file__).parent / "steam_data"
EXPORT_DIR = Path(__file__).parent / "exports"
KNOWN_APPS_FILE = DATA_DIR / "applist.json"
WATCHLIST_FILE = DATA_DIR / "early_stage_watchlist.json"  # New file for tracking early-stage apps

# Words that indicate different versions of the same game
VERSION_SUFFIXES = {
    "demo", "playtest", "beta", "alpha", "test", "trial", "preview",
    "early access", "prologue", "chapter", "episode", "dlc", "expansion"
}

# Genre-based wishlist multipliers (followers * multiplier = estimated wishlists)
GENRE_MULTIPLIER = {
    # 深度策略类：更低倍数
    "4x": 9, 
    "turn-based strategy": 9, 
    "survival": 9.5,
    "grand strategy": 9,
    "city builder": 9.5,
    # 叙事/休闲类：更高倍数
    "story rich": 13,
    "story-rich": 13, 
    "relaxing": 15, 
    "puzzle": 16,
    "visual novel": 14,
    "dating sim": 15,
    # 中等倍数
    "action": 11,
    "adventure": 12,
    "rpg": 11,
    "simulation": 10,
    "strategy": 10,
    "indie": 12,
    "casual": 14
}

# 正则表达式匹配SteamDB愿望单排名
WISHLIST_RE = re.compile(r'#\s*(\d+)\s+in wishlists')

# Updated fields to include wishlist estimation
FIELDS = [
    "type",
    "name",
    "steam_appid",
    "developers",
    "publishers",
    "website",
    "categories",
    "genres",
    "tags",
    "steam_url",
    "detection_stage",  # New field: "public_unreleased", "early_stage", "minimal_data"
    "api_response_type",  # New field: "full_details", "minimal_data", "no_response"
    "potential_duplicate",  # New field: indicates if this might be a duplicate/variant
    "release_date",       # New field: game release date
    "description",        # New field: game description for understanding gameplay
    "content_descriptor_notes",
    "supported_languages", # New field: supported languages list
    "followers",          # New field: Steam community followers count
    "wishlists_est",      # New field: estimated wishlist count
    "wishlist_rank",      # New field: SteamDB wishlist ranking
    "discovery_date"      # New field: when we first detected this app (moved to end)
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
APPLIST_PAGE_SIZE = int(os.environ.get("APPLIST_PAGE_SIZE", "50000"))
STEAM_API_KEY = os.environ.get("STEAM_API_KEY") or os.environ.get("WEBAPI_KEY")


def _env_flag(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


FOLLOWER_FETCH_ENABLED = _env_flag("FETCH_FOLLOWERS", "true")
try:
    FOLLOWER_SAMPLE_RATE = float(os.environ.get("FOLLOWER_SAMPLE_RATE", "1.0"))
except ValueError:
    FOLLOWER_SAMPLE_RATE = 1.0
FOLLOWER_SAMPLE_RATE = max(0.0, min(1.0, FOLLOWER_SAMPLE_RATE))
FOLLOWER_FETCH_DELAY = float(os.environ.get("FOLLOWER_FETCH_DELAY", "0.0"))

WISHLIST_RANK_FETCH_ENABLED = _env_flag("FETCH_WISHLIST_RANK", "true")
WISHLIST_RANK_MIN_FOLLOWERS = int(os.environ.get("WISHLIST_RANK_MIN_FOLLOWERS", "100"))
WISHLIST_RANK_DELAY = float(os.environ.get("WISHLIST_RANK_DELAY", "0.5"))

def fetch_applist_via_store_service(api_key: str, page_size: int = 50000) -> List[Dict]:
    """Fetch applist via IStoreService (requires a Steam Web API key)."""
    apps: List[Dict] = []
    last_appid = 0
    page_size = min(page_size, 50000)  # API caps at 50k per page

    while True:
        params = {
            "key": api_key,
            "last_appid": last_appid,
            "max_results": page_size,
            "include_games": True,
            "include_dlc": True,
            "include_software": True,
            "include_videos": False,
            "include_hardware": False,
        }
        resp = requests.get(STORE_APP_LIST_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        chunk = data.get("response", {}).get("apps", []) or []
        if not chunk:
            break
        apps.extend(chunk)
        last_appid = chunk[-1].get("appid", last_appid)
        if len(chunk) < page_size:
            break

    return apps


def fetch_full_applist() -> List[Dict]:
    """Download the full Steam app list with fallbacks and caching."""
    # 1) Preferred: IStoreService (needs STEAM_API_KEY)
    if STEAM_API_KEY:
        try:
            apps = fetch_applist_via_store_service(STEAM_API_KEY, page_size=APPLIST_PAGE_SIZE)
            if apps:
                return apps
            logger.warning("IStoreService applist returned empty payload.")
        except Exception as exc:
            logger.warning("IStoreService applist failed: %s", exc)
    else:
        logger.warning(
            "STEAM_API_KEY not set; falling back to legacy public endpoints that are currently returning 404 from Steam."
        )

    # 2) Legacy open endpoints (recently started returning 404; kept for compatibility)
    last_error: Optional[Exception] = None
    for url in LEGACY_APPLIST_URLS:
        resp = None
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            apps = data.get("applist", {}).get("apps", []) or data.get("apps", [])
            if apps:
                if url != LEGACY_APPLIST_URLS[0]:
                    logger.warning("Applist legacy fallback URL succeeded: %s", url)
                return apps
            logger.warning("Applist response empty from %s (keys: %s)", url, list(data.keys()))
        except Exception as exc:
            last_error = exc
            logger.warning("Applist fetch failed from %s: %s", url, exc)
            if resp is not None:
                try:
                    logger.warning("Response snippet: %s", resp.text[:200])
                except Exception:
                    pass

    # 3) Cache fallback so the crawler still runs (won't detect new apps)
    if KNOWN_APPS_FILE.exists():
        logger.warning(
            "Falling back to cached applist from %s; new apps will not be detected until network access is restored or a valid key is provided.",
            KNOWN_APPS_FILE,
        )
        with KNOWN_APPS_FILE.open("r", encoding="utf-8") as f:
            cached_ids = json.load(f)
        return [{"appid": appid, "name": ""} for appid in cached_ids]

    raise RuntimeError(f"Failed to fetch applist; last error: {last_error}")

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
            details["store_tags"] = fetch_store_tags(appid)
            details["_api_response"] = "success"
        return details
    except Exception as e:
        # Capture network/parsing errors too
        return {"_api_response": "error", "_app_id": appid, "_error": str(e)}


def fetch_store_tags(appid: int, session: requests.Session = None) -> List[str]:
    """Fetch visible Steam store tags from the public app page."""
    sess = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (SteamStoreTagBot/1.0)",
        "Cookie": "birthtime=0; mature_content=1; wants_mature_content=1",
    }
    try:
        resp = sess.get(STORE_PAGE_URL_TEMPLATE.format(appid=appid), headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        tags = []
        for tag_el in soup.select(".glance_tags.popular_tags a.app_tag, .glance_tags.popular_tags .app_tag"):
            tag_text = clean_text_content(tag_el.get_text(" ", strip=True))
            if not tag_text or tag_text == "+":
                continue
            if tag_text not in tags:
                tags.append(tag_text)
            if len(";".join(tags)) >= 480 or len(tags) >= 12:
                break
        return tags
    except Exception as exc:
        logging.warning("Store tags fetch failed for %s: %s", appid, exc)
        return []

def fetch_follower_count(appid: int, session: requests.Session = None) -> Optional[int]:
    """获取Steam社区关注者数量"""
    sess = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (FollowerBot/1.0)",
        "Cookie": "birthtime=0"   # 绕过年龄墙
    }
    try:
        resp = sess.get(FOLLOWER_URL.format(appid=appid), headers=headers, timeout=15)
        if resp.status_code in (403, 429):
            logging.warning(
                "Follower fetch blocked for %s (status %s). Consider lowering MAX_WORKERS or increasing FOLLOWER_FETCH_DELAY.",
                appid,
                resp.status_code,
            )
            return None
        resp.raise_for_status()
        try:
            xml_root = ET.fromstring(resp.text)
        except ET.ParseError as parse_err:
            logging.warning("Follower fetch parse failed for %s: %s", appid, parse_err)
            return None
        member_tag = xml_root.find("./groupDetails/memberCount")
        return int(member_tag.text) if member_tag is not None else None
    except Exception as e:
        logging.warning("Follower fetch failed for %s: %s", appid, e)
        return None

def estimate_wishlists(followers: int, genres: Optional[List[str]] = None) -> int:
    """基于关注者数和游戏类型估算愿望单数量"""
    base = 12       # 全站中位数
    if genres:
        for genre in genres:
            genre_lower = genre.lower()
            if genre_lower in GENRE_MULTIPLIER:
                base = GENRE_MULTIPLIER[genre_lower]
                break
    return int(followers * base) if followers else 0

def fetch_wishlist_rank(appid: int, session: requests.Session = None) -> int | None:
    """获取SteamDB愿望单排名"""
    if not WISHLIST_RANK_FETCH_ENABLED:
        return None
    sess = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (SteamDBBot/1.0)"
    }
    try:
        url = STEAMDB_URL.format(appid=appid)
        resp = sess.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        m = WISHLIST_RE.search(resp.text)
        return int(m.group(1)) if m else None
    except Exception as e:
        logging.warning("Wishlist rank fetch failed for %s: %s", appid, e)
        return None

def clean_text_content(text: str) -> str:
    """清理文本内容：解码HTML实体，移除HTML标签，规范化空白字符"""
    if not text:
        return ""
    
    # 解码HTML实体 (如 &quot; -> ", &amp; -> &, &lt; -> <, &gt; -> >)
    text = html.unescape(text)
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 规范化空白字符：将多个连续空白字符（包括换行、制表符）替换为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 移除首尾空白
    text = text.strip()
    
    return text

def fetch_wishlist_data(appid: int, details: Dict = None, session: requests.Session = None) -> Dict:
    """获取完整的愿望单估算数据"""
    if not FOLLOWER_FETCH_ENABLED:
        return {"followers": None, "wishlists_est": None, "wishlist_rank": None}

    if FOLLOWER_SAMPLE_RATE < 1.0 and random.random() > FOLLOWER_SAMPLE_RATE:
        return {"followers": None, "wishlists_est": None, "wishlist_rank": None}

    sess = session or requests.Session()
    if FOLLOWER_FETCH_DELAY > 0:
        time.sleep(FOLLOWER_FETCH_DELAY)
    
    # 获取关注者数
    followers = fetch_follower_count(appid, sess)
    
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
        
        wishlists_est = estimate_wishlists(followers, genres)
    
    # 获取SteamDB排名（可选，因为只有热门游戏才有排名）
    wishlist_rank = None
    if (
        WISHLIST_RANK_FETCH_ENABLED
        and followers
        and followers >= WISHLIST_RANK_MIN_FOLLOWERS
    ):
        if WISHLIST_RANK_DELAY > 0:
            time.sleep(WISHLIST_RANK_DELAY)
        wishlist_rank = fetch_wishlist_rank(appid, sess)
    
    return {
        "followers": followers,
        "wishlists_est": wishlists_est,
        "wishlist_rank": wishlist_rank
    }

def get_game_details(appid: int, session: requests.Session) -> Dict:
    """
    获取单个游戏的详细信息
    """
    try:
        url = DETAILS_URL_TEMPLATE.format(appid=appid)
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if str(appid) in data and data[str(appid)]['success']:
            game_data = data[str(appid)]['data']
            
            # 检查是否为游戏类型
            if game_data.get('type') != 'game':
                return None
                
            # 提取基本信息
            name = game_data.get('name', '')
            
            # 提取发布日期
            release_date = "未知"
            release_date_info = game_data.get('release_date', {})
            if release_date_info and not release_date_info.get('coming_soon', True):
                release_date = release_date_info.get('date', '未知')
            
            # 提取游戏描述（短描述优先，如果没有则使用详细描述的前200字）
            description = ""
            if game_data.get('short_description'):
                description = clean_text_content(game_data.get('short_description', ''))
            elif game_data.get('detailed_description'):
                # 清理HTML内容并截取前200字符
                detailed_desc = game_data.get('detailed_description', '')
                clean_desc = clean_text_content(detailed_desc)
                description = clean_desc[:200] + '...' if len(clean_desc) > 200 else clean_desc
            
            # 提取支持语言
            supported_languages = []
            if game_data.get('supported_languages'):
                # Steam返回的语言是HTML格式，需要解析
                import re
                lang_text = game_data.get('supported_languages', '')
                # 提取语言名称（移除HTML标签和额外说明）
                languages = re.findall(r'>([^<]+)<', lang_text)
                if not languages:
                    # 如果没有找到HTML标签，可能是纯文本
                    languages = [lang.strip() for lang in lang_text.split(',')]
                supported_languages = [lang.strip() for lang in languages if lang.strip()]
            
            # 提取开发商和发行商
            developers = game_data.get('developers', [])
            publishers = game_data.get('publishers', [])
            
            # 提取Steam标签/分类
            categories = []
            if game_data.get('categories'):
                categories = [cat.get('description', '') for cat in game_data.get('categories', [])]
            
            genres = []
            if game_data.get('genres'):
                genres = [genre.get('description', '') for genre in game_data.get('genres', [])]

            content_descriptor_notes = ""
            content_descriptors = game_data.get("content_descriptors") or {}
            if isinstance(content_descriptors, dict):
                content_descriptor_notes = clean_text_content(content_descriptors.get("notes", ""))

            store_tags = fetch_store_tags(appid, session)
            
            return {
                'appid': appid,
                'name': name,
                'release_date': release_date,
                'description': description,
                'supported_languages': supported_languages,
                'developers': developers,
                'publishers': publishers,
                'categories': categories,
                'genres': genres,
                'tags': store_tags,
                'website': game_data.get('website'),
                'content_descriptor_notes': content_descriptor_notes,
                'steam_url': f"https://store.steampowered.com/app/{appid}/",
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }
        
        return None
        
    except Exception as e:
        logging.error(f"获取游戏 {appid} 详情时出错: {e}")
        return None

def build_row(details: Dict, app_id: int = None, wishlist_data: Dict = None) -> Dict:
    """Enhanced to capture early-stage apps with minimal data and wishlist estimation"""
    discovery_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Extract wishlist data if provided
    followers = wishlist_data.get("followers") if wishlist_data else None
    wishlists_est = wishlist_data.get("wishlists_est") if wishlist_data else None
    wishlist_rank = wishlist_data.get("wishlist_rank") if wishlist_data else None

    content_descriptor_notes = ""
    content_descriptors = details.get("content_descriptors") if details else {}
    if isinstance(content_descriptors, dict):
        content_descriptor_notes = clean_text_content(content_descriptors.get("notes", ""))
    
    # Handle new data structure from get_game_details
    if details and details.get('appid'):
        # This is from the new get_game_details function
        return {
            "type": "game",
            "name": details.get("name", ""),
            "steam_appid": str(details.get("appid", "")),
            "developers": ";".join(details.get("developers", [])) if details.get("developers") else None,
            "publishers": ";".join(details.get("publishers", [])) if details.get("publishers") else None,
            "website": details.get("website"),
            "categories": ";".join(details.get("categories", [])) if details.get("categories") else None,
            "genres": ";".join(details.get("genres", [])) if details.get("genres") else None,
            "tags": ";".join(details.get("tags", [])) if details.get("tags") else None,
            "steam_url": details.get("steam_url", ""),
            "detection_stage": "public_unreleased",  # Assuming these are unreleased games
            "api_response_type": "full_details",
            "potential_duplicate": False,
            "release_date": details.get("release_date", "未知"),
            "description": details.get("description", ""),
            "content_descriptor_notes": details.get("content_descriptor_notes", ""),
            "supported_languages": ";".join(details.get("supported_languages", [])) if details.get("supported_languages") else None,
            "followers": followers,
            "wishlists_est": wishlists_est,
            "wishlist_rank": wishlist_rank,
            "discovery_date": discovery_date
        }
    
    # Handle early-stage apps that only have minimal data
    if details and details.get("_api_response") in ["failed", "error"]:
        return {
            "type": "unknown",
            "name": f"Early Stage App (ID: {app_id or details.get('_app_id', 'unknown')})",
            "steam_appid": str(app_id or details.get("_app_id", "")),
            "developers": None,
            "publishers": None,
            "website": None,
            "categories": None,
            "genres": None,
            "tags": None,
            "steam_url": f"https://store.steampowered.com/app/{app_id or details.get('_app_id', '')}" if app_id or details.get('_app_id') else None,
            "detection_stage": "early_stage",
            "api_response_type": details.get("_api_response", "no_response"),
            "potential_duplicate": False,
            "release_date": "未知",
            "description": "",
            "content_descriptor_notes": "",
            "supported_languages": None,
            "followers": followers,
            "wishlists_est": wishlists_est,
            "wishlist_rank": wishlist_rank,
            "discovery_date": discovery_date
        }
    
    # Handle apps with full details (legacy data structure)
    name = details.get("name")
    if name:
        # Check if it's a released game we should skip
        release_info = details.get("release_date", {})
        if release_info.get("coming_soon") is False:  # Explicitly released
            return {}  # Skip clearly released games
        
        # Include unreleased games with full store pages
        detection_stage = "public_unreleased" if release_info.get("coming_soon") else "minimal_data"
        
        # Extract release date from legacy structure
        release_date = "未知"
        if release_info and release_info.get("date"):
            release_date = release_info.get("date")
        
        # Extract description from legacy structure
        description = ""
        if details.get("short_description"):
            description = clean_text_content(details.get("short_description"))
        elif details.get("detailed_description"):
            detailed_desc = details.get("detailed_description", "")
            clean_desc = clean_text_content(detailed_desc)
            description = clean_desc[:200] + '...' if len(clean_desc) > 200 else clean_desc
        
        # Extract supported languages from legacy structure
        supported_languages = []
        if details.get("supported_languages"):
            import re
            lang_text = details.get("supported_languages", "")
            languages = re.findall(r'>([^<]+)<', lang_text)
            if not languages:
                languages = [lang.strip() for lang in lang_text.split(',')]
            supported_languages = [lang.strip() for lang in languages if lang.strip()]
        
    else:
        # Apps without names are likely very early stage
        detection_stage = "minimal_data"
        name = f"Unnamed App (ID: {details.get('steam_appid', app_id or 'unknown')})"
        release_date = "未知"
        description = ""
        supported_languages = []
    
    return {
        "type": details.get("type", "unknown"),
        "name": name,
        "steam_appid": str(details.get("steam_appid", app_id or "")),
        "developers": ";".join(details.get("developers", [])) if details.get("developers") else None,
        "publishers": ";".join(details.get("publishers", [])) if details.get("publishers") else None,
        "website": details.get("website"),
        "categories": ";".join(c.get("description") for c in details.get("categories", [])) if details.get("categories") else None,
        "genres": ";".join(g.get("description") for g in details.get("genres", [])) if details.get("genres") else None,
        "tags": ";".join(details.get("store_tags", [])) if details.get("store_tags") else None,
        "steam_url": f"https://store.steampowered.com/app/{details.get('steam_appid', app_id or '')}" if details.get('steam_appid') or app_id else None,
        "detection_stage": detection_stage,
        "api_response_type": "full_details",
        "potential_duplicate": False,
        "release_date": release_date,
        "description": description,
        "content_descriptor_notes": content_descriptor_notes,
        "supported_languages": ";".join(supported_languages) if supported_languages else None,
        "followers": followers,
        "wishlists_est": wishlists_est,
        "wishlist_rank": wishlist_rank,
        "discovery_date": discovery_date
    }

def export_csv(rows: List[Dict]) -> Path:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = EXPORT_DIR / f"new_games_{today_str}.csv"
    
    # 使用utf-8-sig编码确保Windows正确显示中文（添加BOM头）
    with file_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            # 清理行数据中的文本字段
            cleaned_row = {}
            for key, value in row.items():
                if isinstance(value, str) and value:
                    # 对可能包含HTML实体的字段进行额外清理
                    if key in ['name', 'description', 'developers', 'publishers', 'categories', 'genres', 'tags', 'content_descriptor_notes']:
                        cleaned_row[key] = clean_text_content(value)
                    else:
                        cleaned_row[key] = value
                else:
                    cleaned_row[key] = value
            writer.writerow(cleaned_row)
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
                
                # Calculate wishlist statistics
                total_followers = sum(int(row.get('followers', 0) or 0) for row in rows_data)
                total_wishlists_est = sum(int(row.get('wishlists_est', 0) or 0) for row in rows_data)
                apps_with_rank = sum(1 for row in rows_data if row.get('wishlist_rank'))
                
                email_body = f"""New Steam app discoveries for {date_str}:

📊 Discovery Summary:
• Early-stage apps (no public pages): {early_stage}
• Public unreleased games: {public_unreleased}  
• Minimal data apps: {minimal_data}
• Total discoveries: {len(rows_data)}

📈 Wishlist Analytics:
• Total followers across all games: {total_followers:,}
• Estimated total wishlists: {total_wishlists_est:,}
• Games with SteamDB wishlist ranking: {apps_with_rank}

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
            "website": "https://example.com",
            "categories": "Action;Adventure",
            "genres": "RPG;Simulation",
            "steam_url": "https://store.steampowered.com/app/999999",
            "detection_stage": "public_unreleased",
            "api_response_type": "full_details",
            "potential_duplicate": False,
            "release_date": "2025-12-31",
            "description": "An exciting RPG adventure with stunning visuals and immersive gameplay.",
            "supported_languages": "English;Chinese;Japanese;Korean",
            "followers": 2500,
            "wishlists_est": 27500,  # 2500 * 11 (RPG multiplier)
            "wishlist_rank": 1250,
            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        },
        {
            "type": "unknown", 
            "name": "Early Stage App (ID: 999998)",
            "steam_appid": "999998",
            "developers": None,
            "publishers": None,
            "website": None,
            "categories": None,
            "genres": None,
            "steam_url": "https://store.steampowered.com/app/999998",
            "detection_stage": "early_stage",
            "api_response_type": "failed",
            "potential_duplicate": False,
            "release_date": "未知",
            "description": "",
            "supported_languages": None,
            "followers": None,
            "wishlists_est": None,
            "wishlist_rank": None,
            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        },
        {
            "type": "game",
            "name": "Minimal Data Game",
            "steam_appid": "999997",
            "developers": None,
            "publishers": None,
            "website": None,
            "categories": None,
            "genres": None,
            "steam_url": "https://store.steampowered.com/app/999997",
            "detection_stage": "minimal_data",
            "api_response_type": "full_details",
            "potential_duplicate": False,
            "release_date": "2025-06-15",
            "description": "A mysterious game with limited information available.",
            "supported_languages": "English",
            "followers": 85,
            "wishlists_est": 1020,  # 85 * 12 (default multiplier)
            "wishlist_rank": None,  # 关注者太少，没有排名
            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
    ]
    
    with file_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in test_data:
            writer.writerow(row)
    
    return file_path

def normalize_game_name(name: str) -> str:
    """Normalize game name for similarity comparison"""
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower().strip()
    
    # Remove common punctuation and special characters
    normalized = re.sub(r'[™®©]', '', normalized)
    normalized = re.sub(r'[:\-–—_]', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Remove common version indicators
    for suffix in VERSION_SUFFIXES:
        # Remove suffix at the end of the name
        pattern = rf'\b{re.escape(suffix)}\b\s*$'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove suffix in parentheses
        pattern = rf'\s*\(\s*{re.escape(suffix)}\s*\)\s*'
        normalized = re.sub(pattern, ' ', normalized, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two game names (0.0 to 1.0)"""
    if not name1 or not name2:
        return 0.0
    
    # Normalize both names
    norm1 = normalize_game_name(name1)
    norm2 = normalize_game_name(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Use SequenceMatcher for similarity calculation
    return SequenceMatcher(None, norm1, norm2).ratio()

def find_similar_games(new_name: str, existing_games: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """Find games with similar names in the existing list"""
    similar_games = []
    
    for game in existing_games:
        existing_name = game.get("name", "")
        similarity = calculate_name_similarity(new_name, existing_name)
        
        if similarity >= threshold:
            similar_games.append({
                "game": game,
                "similarity": similarity,
                "normalized_new": normalize_game_name(new_name),
                "normalized_existing": normalize_game_name(existing_name)
            })
    
    # Sort by similarity (highest first)
    similar_games.sort(key=lambda x: x["similarity"], reverse=True)
    return similar_games

def check_developer_match(new_developers: List[str], existing_developers: List[str]) -> bool:
    """Check if developers match between two games"""
    if not new_developers or not existing_developers:
        return False
    
    # Convert to sets for comparison (case insensitive)
    new_devs = {dev.lower().strip() for dev in new_developers if dev}
    existing_devs = {dev.lower().strip() for dev in existing_developers if dev}
    
    # Check if there's any overlap
    return bool(new_devs.intersection(existing_devs))

def get_version_type(name: str) -> str:
    """Determine what type of version this game is (demo, beta, etc.)"""
    if not name:
        return "main"
    
    name_lower = name.lower()
    
    for suffix in VERSION_SUFFIXES:
        if suffix in name_lower:
            return suffix
    
    return "main"

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
    watchlist_nsfw_filtered = 0
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
                    is_nsfw, nsfw_reasons = classify_nsfw_from_details(details)
                    if is_nsfw:
                        watchlist_nsfw_filtered += 1
                        logger.info(
                            "Filtered NSFW watchlist app %s: %s [%s]",
                            aid_int,
                            details.get("name"),
                            ", ".join(nsfw_reasons),
                        )
                        if aid_str in watchlist:
                            del watchlist[aid_str]
                        continue

                    # App became accessible! Fetch wishlist data too
                    wishlist_data = fetch_wishlist_data(aid_int, details)
                    row = build_row(details, aid_int, wishlist_data)
                    if row:
                        watchlist_promotions.append((aid_int, details, row))
                        logger.info("🎉 Watchlist app %s became accessible: %s (followers: %s, est. wishlists: %s)", 
                                  aid_int, details.get("name"), 
                                  wishlist_data.get("followers"), wishlist_data.get("wishlists_est"))
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
    nsfw_filtered_count = 0
    new_to_watchlist = 0
    
    def _task(aid):
        details = fetch_app_details(aid)
        wishlist_data = None
        is_nsfw = False
        nsfw_reasons: list[str] = []
        if details and details.get("_api_response") == "success" and details.get("name"):
            is_nsfw, nsfw_reasons = classify_nsfw_from_details(details)
            if not is_nsfw:
                # 只为有成功响应的安全应用获取 wishlist 数据
                wishlist_data = fetch_wishlist_data(aid, details)
        return aid, details, wishlist_data, is_nsfw, nsfw_reasons

    early_stage_count = 0
    public_unreleased_count = 0
    minimal_data_count = 0
    
    # Process new apps
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(_task, aid): aid for aid in new_ids}
        for idx, fut in enumerate(as_completed(futures), start=1):
            total_fetched += 1
            aid, details, wishlist_data, is_nsfw, nsfw_reasons = fut.result()
            if is_nsfw:
                nsfw_filtered_count += 1
                logger.info(
                    "Filtered NSFW app %s: %s [%s]",
                    aid,
                    details.get("name"),
                    ", ".join(nsfw_reasons),
                )
                continue
            row = build_row(details, aid, wishlist_data)
            
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

    logger.info(
        "Discovery summary: %d apps processed, %d released (filtered), %d NSFW (filtered), %d early-stage (watchlisted), %d public unreleased, %d minimal data",
        total_fetched,
        already_released_filtered,
        nsfw_filtered_count,
        early_stage_count,
        public_unreleased_count,
        minimal_data_count,
    )
    
    if watchlist_promotions:
        logger.info("Promoted %d apps from watchlist to known apps", len(watchlist_promotions))

    if watchlist_nsfw_filtered:
        logger.info("Removed %d NSFW apps from watchlist", watchlist_nsfw_filtered)
    
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
