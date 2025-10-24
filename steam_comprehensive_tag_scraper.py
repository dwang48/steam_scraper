#!/usr/bin/env python3
"""
Steam全量标签爬虫
搜索Steam上所有特定标签的未发布游戏
支持全量搜索和批量处理，避免API限流
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
    },
    "horror": {
        "tags": ["Horror", "Psychological Horror", "Survival Horror", "Gore", "Dark", "Thriller"],
        "description": "恐怖类游戏"
    },
    "strategy": {
        "tags": ["Strategy", "Turn-Based Strategy", "Real Time Strategy", "Grand Strategy", "4X", "Tower Defense"],
        "description": "策略类游戏"
    },
    "simulation": {
        "tags": ["Simulation", "City Builder", "Management", "Building", "Economy", "Tycoon"],
        "description": "模拟经营游戏"
    },
    "puzzle": {
        "tags": ["Puzzle", "Logic", "Match 3", "Hidden Object", "Platformer", "Physics"],
        "description": "解谜类游戏"
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
    "tag_category",
    "discovery_date"
]

# Setup directories
DATA_DIR = Path(__file__).parent / "steam_data"
EXPORT_DIR = Path(__file__).parent / "exports"
PROGRESS_DIR = Path(__file__).parent / "progress"  # 新增：进度保存目录
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
PROGRESS_DIR.mkdir(exist_ok=True)

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("steam_comprehensive")

def fetch_full_applist() -> List[Dict]:
    """Download the full Steam app list."""
    logger.info("获取完整的Steam应用列表...")
    resp = requests.get(APPLIST_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    apps = data.get("applist", {}).get("apps", [])
    logger.info(f"找到 {len(apps):,} 个Steam应用")
    return apps

def save_progress(category: str, processed_ids: Set[int], found_games: List[Dict]):
    """保存搜索进度"""
    progress_file = PROGRESS_DIR / f"{category}_progress.json"
    progress_data = {
        "processed_ids": list(processed_ids),
        "found_games": found_games,
        "last_update": datetime.now(timezone.utc).isoformat(),
        "total_processed": len(processed_ids),
        "total_found": len(found_games)
    }
    
    with progress_file.open("w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"进度已保存: {category} - 已处理 {len(processed_ids):,} 个，找到 {len(found_games)} 个游戏")

def load_progress(category: str) -> tuple[Set[int], List[Dict]]:
    """加载搜索进度"""
    progress_file = PROGRESS_DIR / f"{category}_progress.json"
    
    if progress_file.exists():
        try:
            with progress_file.open("r", encoding="utf-8") as f:
                progress_data = json.load(f)
            
            processed_ids = set(progress_data.get("processed_ids", []))
            found_games = progress_data.get("found_games", [])
            
            logger.info(f"已加载进度: {category} - 已处理 {len(processed_ids):,} 个，找到 {len(found_games)} 个游戏")
            return processed_ids, found_games
        except Exception as e:
            logger.warning(f"加载进度失败: {e}")
    
    return set(), []

def fetch_app_details(appid: int, session: requests.Session = None) -> Optional[Dict]:
    """安全地获取应用详情，包含重试机制"""
    sess = session or requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    url = DETAILS_URL_TEMPLATE.format(appid=appid)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # 渐进式延迟
            delay = 1.5 + (attempt * 1.0)
            time.sleep(delay)
            
            resp = sess.get(url, headers=headers, timeout=20)
            
            if resp.status_code == 403:
                return None
                
            if resp.status_code == 429:
                wait_time = 60 * (attempt + 1)
                logger.warning(f"API限流 {appid}，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                continue
            
            resp.raise_for_status()
            data = resp.json().get(str(appid), {})
            
            if not data.get("success"):
                return None
            
            return data.get("data", {})
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"获取 {appid} 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(5)
                continue
            else:
                return None
    
    return None

def clean_text_content(text: str) -> str:
    """清理HTML内容"""
    if not text:
        return ""
    
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_tags_from_details(details: Dict) -> List[str]:
    """从游戏详情中提取标签"""
    all_tags = []
    
    if details.get('categories'):
        for cat in details['categories']:
            if isinstance(cat, dict) and cat.get('description'):
                all_tags.append(cat['description'])
    
    if details.get('genres'):
        for genre in details['genres']:
            if isinstance(genre, dict) and genre.get('description'):
                all_tags.append(genre['description'])
    
    return all_tags

def check_target_tags(available_tags: List[str], target_category: str) -> List[str]:
    """检查是否包含目标标签"""
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
    """检查游戏是否未发布"""
    if details.get('type') != 'game':
        return False
    
    release_info = details.get('release_date', {})
    
    # 明确标记为即将发布
    if release_info.get('coming_soon') is True:
        return True
    
    # 明确标记为已发布
    if release_info.get('coming_soon') is False:
        return False
    
    # 检查未来日期
    release_date = release_info.get('date', '')
    if release_date and release_date.lower() not in ['tba', 'to be announced', 'coming soon']:
        try:
            from dateutil import parser as dateparser
            parsed_date = dateparser.parse(release_date)
            return parsed_date > datetime.now()
        except:
            pass
    
    # 默认认为是未发布（如果信息不明确）
    return True

def process_app_for_category(appid: int, session: requests.Session, target_category: str) -> Optional[Dict]:
    """为特定类别处理单个应用"""
    details = fetch_app_details(appid, session)
    
    if not details:
        return None
    
    if not is_unreleased_game(details):
        return None
    
    available_tags = extract_tags_from_details(details)
    found_target_tags = check_target_tags(available_tags, target_category)
    
    if not found_target_tags:
        return None
    
    # 提取详细信息
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

def search_category_comprehensive(all_app_ids: List[int], target_category: str, max_finds: int = None, resume: bool = True) -> List[Dict]:
    """全量搜索特定类别的游戏"""
    category_info = TAG_CATEGORIES[target_category]
    logger.info(f"开始全量搜索 {category_info['description']}...")
    logger.info(f"目标标签: {', '.join(category_info['tags'])}")
    logger.info(f"总应用数: {len(all_app_ids):,}")
    
    # 加载进度
    processed_ids, found_games = load_progress(target_category) if resume else (set(), [])
    
    # 过滤已处理的应用
    remaining_ids = [aid for aid in all_app_ids if aid not in processed_ids]
    logger.info(f"剩余未处理: {len(remaining_ids):,} 个应用")
    
    if max_finds and len(found_games) >= max_finds:
        logger.info(f"已找到足够的游戏 ({len(found_games)}/{max_finds})，跳过搜索")
        return found_games
    
    session = requests.Session()
    save_interval = 100  # 每处理100个应用保存一次进度
    
    try:
        for i, appid in enumerate(remaining_ids):
            if max_finds and len(found_games) >= max_finds:
                logger.info(f"已达到目标数量 ({max_finds})，停止搜索")
                break
            
            try:
                result = process_app_for_category(appid, session, target_category)
                processed_ids.add(appid)
                
                if result:
                    found_games.append(result)
                    logger.info(f"✓ 找到 {category_info['description']}: {result['name']} (标签: {result['target_tags_found']})")
                
                # 定期保存进度
                if (i + 1) % save_interval == 0:
                    save_progress(target_category, processed_ids, found_games)
                    progress_pct = ((len(processed_ids)) / len(all_app_ids)) * 100
                    logger.info(f"进度: {len(processed_ids):,}/{len(all_app_ids):,} ({progress_pct:.1f}%) - 已找到 {len(found_games)} 个游戏")
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，保存进度...")
                save_progress(target_category, processed_ids, found_games)
                raise
            except Exception as e:
                processed_ids.add(appid)  # 标记为已处理，避免重复
                logger.warning(f"处理应用 {appid} 时出错: {e}")
        
        # 最终保存
        save_progress(target_category, processed_ids, found_games)
        
    finally:
        session.close()
    
    return found_games

def export_category_results(results: List[Dict], category: str) -> Path:
    """导出分类结果"""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = EXPORT_DIR / f"steam_comprehensive_{category}_games_{today_str}.csv"
    
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
        description="Steam全量标签爬虫 - 搜索所有未发布的特定标签游戏",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
标签类型:
  narrative    - 叙事类游戏
  emotional    - 情感类游戏  
  co-op        - 合作类游戏
  cozy         - 温馨休闲游戏
  horror       - 恐怖类游戏
  strategy     - 策略类游戏
  simulation   - 模拟经营游戏
  puzzle       - 解谜类游戏

示例用法:
  python steam_comprehensive_tag_scraper.py --all --max-finds 10
  python steam_comprehensive_tag_scraper.py --category narrative --max-finds 50
  python steam_comprehensive_tag_scraper.py --category co-op  # 搜索所有co-op游戏
  python steam_comprehensive_tag_scraper.py --resume-category narrative  # 恢复中断的搜索

特点:
- 搜索所有Steam应用，不限数量
- 只返回未发布的游戏  
- 支持断点恢复，可以中断后继续
- 自动保存进度，避免重复工作
- 智能重试和错误处理
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all", 
        action="store_true",
        help="搜索所有类型的游戏"
    )
    group.add_argument(
        "--category",
        choices=list(TAG_CATEGORIES.keys()),
        help="搜索特定类型的游戏"
    )
    group.add_argument(
        "--resume-category",
        choices=list(TAG_CATEGORIES.keys()),
        help="恢复特定类型的搜索"
    )
    
    parser.add_argument(
        "--max-finds", 
        type=int, 
        help="每种类型最多找到多少个游戏（不限制则搜索全部）"
    )
    
    parser.add_argument(
        "--no-resume", 
        action="store_true",
        help="不加载之前的进度，重新开始搜索"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Steam全量标签爬虫启动")
    logger.info("="*60)
    
    # 获取完整应用列表
    all_apps = fetch_full_applist()
    all_app_ids = [app['appid'] for app in all_apps]
    
    resume = not args.no_resume
    
    if args.all:
        # 搜索所有类别
        logger.info(f"将搜索所有 {len(TAG_CATEGORIES)} 种类型的游戏")
        if args.max_finds:
            logger.info(f"每种类型最多找 {args.max_finds} 个游戏")
        
        all_results = {}
        
        for category in TAG_CATEGORIES.keys():
            logger.info(f"\n{'='*50}")
            try:
                results = search_category_comprehensive(all_app_ids, category, args.max_finds, resume)
                all_results[category] = results
                
                if results:
                    csv_path = export_category_results(results, category)
                    logger.info(f"✅ {TAG_CATEGORIES[category]['description']} 完成: {len(results)} 个游戏")
                    logger.info(f"结果已导出: {csv_path}")
                else:
                    logger.info(f"❌ 未找到 {TAG_CATEGORIES[category]['description']} 游戏")
                    
            except KeyboardInterrupt:
                logger.info(f"搜索 {category} 时被中断，可以使用 --resume-category {category} 恢复")
                break
            except Exception as e:
                logger.error(f"搜索 {category} 时出错: {e}")
        
        # 打印总结
        print(f"\n{'='*60}")
        print("搜索总结:")
        total_found = 0
        for category, results in all_results.items():
            count = len(results)
            total_found += count
            print(f"- {TAG_CATEGORIES[category]['description']}: {count} 个游戏")
        print(f"总计找到: {total_found} 个未发布游戏")
    
    elif args.category or args.resume_category:
        # 搜索单个类别
        category = args.category or args.resume_category
        
        if args.resume_category:
            logger.info(f"恢复搜索: {TAG_CATEGORIES[category]['description']}")
        
        try:
            results = search_category_comprehensive(all_app_ids, category, args.max_finds, resume)
            
            if results:
                csv_path = export_category_results(results, category)
                logger.info(f"✅ 搜索完成: {len(results)} 个 {TAG_CATEGORIES[category]['description']} 游戏")
                logger.info(f"结果已导出: {csv_path}")
                
                # 显示找到的游戏
                print(f"\n{'='*60}")
                print(f"找到的 {TAG_CATEGORIES[category]['description']}:")
                for i, result in enumerate(results[:10], 1):  # 只显示前10个
                    print(f"{i}. {result['name']}")
                    print(f"   标签: {result['target_tags_found']}")
                    print(f"   发布日期: {result['release_date']}")
                    print(f"   Steam: {result['steam_url']}")
                    print()
                
                if len(results) > 10:
                    print(f"... 还有 {len(results) - 10} 个游戏，详见CSV文件")
            else:
                logger.info(f"未找到 {TAG_CATEGORIES[category]['description']} 游戏")
                
        except KeyboardInterrupt:
            logger.info("搜索被中断，进度已保存。可以使用 --resume-category 恢复")
    
    logger.info("搜索完成！")

if __name__ == "__main__":
    main()












