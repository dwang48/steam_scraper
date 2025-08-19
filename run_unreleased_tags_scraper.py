#!/usr/bin/env python3
"""
Steam未发布游戏标签爬虫运行脚本
专门查找包含co-op, emotional, narrative标签的未发布游戏

使用方法:
python run_unreleased_tags_scraper.py --limit 1000  # 只处理前1000个应用
python run_unreleased_tags_scraper.py --full        # 处理所有应用（可能需要几小时）
"""

import argparse
import logging
from pathlib import Path
from steam_unreleased_tags_scraper import main as run_full_scraper
from steam_unreleased_tags_scraper import (
    fetch_full_applist, 
    search_by_batch,
    export_results,
    logger,
    ALL_TARGET_TAGS
)

def run_limited_scraper(limit: int = 1000):
    """运行限制数量的爬虫，用于快速测试或部分扫描"""
    logger.info(f"Starting LIMITED Steam unreleased games scraper (max {limit} apps)...")
    logger.info(f"Target tags: {', '.join(ALL_TARGET_TAGS)}")
    
    # 获取Steam应用列表
    all_apps = fetch_full_applist()
    
    # 按照应用ID排序，取最新的应用（通常ID越大越新）
    sorted_apps = sorted(all_apps, key=lambda x: x['appid'], reverse=True)
    limited_apps = [app['appid'] for app in sorted_apps[:limit]]
    
    logger.info(f"Processing {len(limited_apps)} most recent apps...")
    
    # 处理应用
    results = search_by_batch(limited_apps, 1, 1)
    
    # 导出结果
    if results:
        csv_path = export_results(results)
        logger.info(f"✅ Found {len(results)} unreleased games with target tags!")
        logger.info(f"Results exported to: {csv_path}")
        
        # 打印摘要
        print("\n" + "="*60)
        print("发现的游戏:")
        for result in results:
            print(f"- {result['name']}")
            print(f"  标签: {result['target_tags_found']}")
            print(f"  发布日期: {result['release_date']}")
            print(f"  Steam链接: {result['steam_url']}")
            print()
    else:
        logger.info("No unreleased games found with the target tags in the limited set.")

def main():
    parser = argparse.ArgumentParser(
        description="Steam未发布游戏标签爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_unreleased_tags_scraper.py --limit 500   # 快速扫描最新500个应用
  python run_unreleased_tags_scraper.py --limit 2000  # 扫描最新2000个应用  
  python run_unreleased_tags_scraper.py --full        # 完整扫描所有应用
  python run_unreleased_tags_scraper.py --test        # 运行测试模式

目标标签: co-op, emotional, narrative相关标签
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--limit", 
        type=int, 
        help="限制处理的应用数量（推荐500-2000进行快速扫描）"
    )
    group.add_argument(
        "--full", 
        action="store_true", 
        help="处理所有Steam应用（警告：可能需要几小时时间）"
    )
    group.add_argument(
        "--test",
        action="store_true",
        help="运行测试模式，使用预定义的少量应用ID"
    )
    
    args = parser.parse_args()
    
    if args.test:
        print("运行测试模式...")
        import subprocess
        subprocess.run(["python", "test_unreleased_tags_scraper.py"])
    elif args.full:
        print("运行完整扫描模式...")
        print("⚠️  警告：这可能需要几个小时时间，请确保网络稳定")
        run_full_scraper()
    else:
        print(f"运行限制模式，处理最新{args.limit}个应用...")
        run_limited_scraper(args.limit)

if __name__ == "__main__":
    main()




