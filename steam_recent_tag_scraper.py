#!/usr/bin/env python3
"""
Steam 高 AppID（最新）标签爬虫 - 快速且稳定（重构版）
- 仅扫描 AppID 最大的前 K 个（通常是最新条目）
- 仅返回未发布（coming_soon/TBA）的游戏
- 一次请求详情，结果同时匹配多个分类（避免重复请求）
- 分批处理、流式写入 CSV，每批输出进度，避免长时间无输出
- 小并发 + 节流，尽量不触发限流

示例：
  python steam_recent_tag_scraper.py --categories narrative co-op cozy emotional --top-k 80000 --workers 6 --delay 0.6
  python steam_recent_tag_scraper.py --categories co-op --top-k 50000 --workers 4 --delay 0.7
  python steam_recent_tag_scraper.py --categories narrative co-op --top-k 20000 --batch-size 500 --progress-every 200
"""

import argparse
import csv
import html
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

APPLIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
APPDETAILS_TPL = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"

# 目标分类标签（基于 appdetails 的 genres/categories 文本做包含匹配）
# 注意：Steam API 的 genres/categories 字段有限，需要更宽松的匹配
TAG_CATEGORIES: Dict[str, List[str]] = {
    "narrative": ["Story", "Narrative", "Interactive Fiction", "Visual Novel", "Text-Based", "Adventure", "RPG", "Choose"],
    "emotional": ["Drama", "Psychological", "Atmospheric", "Adventure", "Story", "Indie", "Simulation"],
    "co-op": ["Co-op", "Online Co-Op", "Local Co-Op", "Cooperative", "Multiplayer"],
    "cozy": ["Cozy", "Relaxing", "Wholesome", "Casual", "Peaceful", "Zen", "Family Friendly", "Simulation"],
}

FIELDS = [
    "name",
    "steam_appid",
    "steam_url",
    "release_date",
    "coming_soon",
    "tag_category",
    "genres",
    "categories",
    "developers",
    "publishers",
    "description",
    "supported_languages",
    "website",
    "discovery_date",
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_DIR = Path(__file__).parent
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("steam_recent")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_full_applist(session: requests.Session) -> List[Dict]:
    resp = session.get(APPLIST_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("applist", {}).get("apps", [])


def is_unreleased(details: Dict) -> bool:
    if details.get("type") != "game":
        return False
    rd = details.get("release_date", {}) or {}
    if rd.get("coming_soon") is True:
        return True
    if rd.get("coming_soon") is False:
        return False
    # 模糊日期：有时 date 是 TBA/Coming soon
    date_text = (rd.get("date") or "").lower()
    if any(x in date_text for x in ["tba", "coming", "soon"]):
        return True
    return False


def match_category(details: Dict, category: str) -> bool:
    targets = TAG_CATEGORIES.get(category, [])
    texts: List[str] = []
    
    # 收集 genres
    for g in details.get("genres", []) or []:
        d = g.get("description")
        if d:
            texts.append(d)
    
    # 收集 categories
    for c in details.get("categories", []) or []:
        d = c.get("description")
        if d:
            texts.append(d)
    
    # 对于 narrative 和 emotional，也检查游戏描述和名称
    if category in ["narrative", "emotional"]:
        # 添加游戏名称
        name = details.get("name", "")
        if name:
            texts.append(name)
        
        # 添加简短描述（前100字符）
        desc = details.get("short_description", "")
        if desc and len(desc) > 0:
            texts.append(desc[:200])  # 检查描述的前200字符
    
    if not texts:
        return False
    
    lower = [t.lower() for t in texts]
    
    # 特殊处理：narrative 类别的更宽松匹配
    if category == "narrative":
        narrative_keywords = ["story", "narrative", "tale", "adventure", "rpg", "visual novel", "choices", "decision"]
        for keyword in narrative_keywords:
            if any(keyword in text for text in lower):
                return True
    
    # 特殊处理：emotional 类别的更宽松匹配
    if category == "emotional":
        emotional_keywords = ["emotional", "drama", "psychological", "atmospheric", "deep", "meaningful", "touching", "heart"]
        for keyword in emotional_keywords:
            if any(keyword in text for text in lower):
                return True
    
    # 标准匹配
    for target in targets:
        tl = target.lower()
        if any(tl in x or x in tl for x in lower):
            return True
    return False


def fetch_details_with_retry(appid: int, session: requests.Session, delay: float) -> Optional[Dict]:
    """单次请求详情，带轻量重试与指数退避。"""
    url = APPDETAILS_TPL.format(appid=appid)
    tries = 3
    backoff = delay
    for i in range(tries):
        time.sleep(backoff)
        try:
            resp = session.get(url, headers=DEFAULT_HEADERS, timeout=20)
            if resp.status_code == 429:  # 限流
                sleep_s = 5 * (i + 1)
                logger.debug(f"429 for {appid}, sleep {sleep_s}s")
                time.sleep(sleep_s)
                backoff *= 1.5
                continue
            if resp.status_code == 403:
                return None
            resp.raise_for_status()
            data = resp.json().get(str(appid), {})
            if not data.get("success"):
                return None
            return data.get("data", {})
        except Exception:
            if i == tries - 1:
                return None
            backoff *= 1.5
    return None


def build_row(details: Dict, category: str) -> Dict:
    rd = (details.get("release_date") or {})
    release_date = rd.get("date") or ""
    desc = details.get("short_description") or ""
    desc = clean_text(desc)
    langs = details.get("supported_languages") or ""
    langs = clean_text(langs) if langs else None
    genres = ";".join([g.get("description", "") for g in details.get("genres", []) if g.get("description")]) or None
    cats = ";".join([c.get("description", "") for c in details.get("categories", []) if c.get("description")]) or None
    devs = ";".join(details.get("developers", []) or []) or None
    pubs = ";".join(details.get("publishers", []) or []) or None
    return {
        "name": details.get("name", ""),
        "steam_appid": str(details.get("steam_appid", "")),
        "steam_url": f"https://store.steampowered.com/app/{details.get('steam_appid','')}/",
        "release_date": release_date,
        "coming_soon": True,
        "tag_category": category,
        "genres": genres,
        "categories": cats,
        "developers": devs,
        "publishers": pubs,
        "description": desc or None,
        "supported_languages": langs,
        "website": details.get("website") or None,
        "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def open_writers(categories: List[str]) -> Tuple[Dict[str, csv.DictWriter], Dict[str, Path], Dict[str, any]]:
    """为每个分类打开一个 CSV 写入器，返回 writers、paths、files。"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    writers: Dict[str, csv.DictWriter] = {}
    paths: Dict[str, Path] = {}
    files: Dict[str, any] = {}
    for cat in categories:
        out = EXPORT_DIR / f"steam_recent_{cat}_unreleased_{today}.csv"
        f = out.open("w", encoding="utf-8-sig", newline="")
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        writers[cat] = w
        paths[cat] = out
        files[cat] = f
    return writers, paths, files

def close_files(files: Dict[str, any]) -> None:
    for f in files.values():
        try:
            f.close()
        except Exception:
            pass


def run(categories: List[str], top_k: int, workers: int, delay: float, batch_size: int, progress_every: int) -> None:
    session = requests.Session()
    try:
        apps = fetch_full_applist(session)
        appids_all = sorted([a["appid"] for a in apps], reverse=True)[:top_k]
        logger.info(f"扫描 AppID Top {top_k}，范围约 {appids_all[0]} -> {appids_all[-1]}")

        writers, paths, files = open_writers(categories)
        matched_counts: Dict[str, int] = {c: 0 for c in categories}

        total = len(appids_all)
        processed = 0

        # 分批处理
        for batch_start in range(0, total, batch_size):
            batch = appids_all[batch_start: batch_start + batch_size]
            logger.info(f"处理批次 {batch_start//batch_size + 1} / {((total + batch_size - 1)//batch_size)}，app 数 {len(batch)}…")

            def fetch_task(aid: int) -> Optional[Dict]:
                d = fetch_details_with_retry(aid, session, delay)
                if not d:
                    return None
                # 仅未发布
                if not is_unreleased(d):
                    return None
                d.setdefault("steam_appid", aid)
                return d

            details_list: List[Optional[Dict]] = []
            with ThreadPoolExecutor(max_workers=workers) as exe:
                futures = [exe.submit(fetch_task, aid) for aid in batch]
                for fut in as_completed(futures):
                    details_list.append(fut.result())
                    processed += 1
                    if processed % progress_every == 0:
                        done_pct = processed * 100.0 / total
                        logger.info(f"进度: {processed}/{total} ({done_pct:.1f}%) | 命中: " + ", ".join(
                            f"{c}:{matched_counts[c]}" for c in categories
                        ))

            # 分类匹配并写入
            for d in filter(None, details_list):
                for cat in categories:
                    if match_category(d, cat):
                        row = build_row(d, cat)
                        writers[cat].writerow(row)
                        matched_counts[cat] += 1

            # 批次总结
            logger.info("批次完成 | 当前命中: " + ", ".join(f"{c}:{matched_counts[c]}" for c in categories))

        # 结束总结
        logger.info("完成扫描 | 最终命中: " + ", ".join(f"{c}:{matched_counts[c]}" for c in categories))
        for cat in categories:
            logger.info(f"导出 {cat}: {paths[cat]}")
    finally:
        try:
            close_files(files)
        except Exception:
            pass
        session.close()


def main():
    p = argparse.ArgumentParser(description="Steam 高 AppID 未发布标签爬虫（快速版，流式输出）")
    p.add_argument("--categories", nargs="+", choices=list(TAG_CATEGORIES.keys()), required=True)
    p.add_argument("--top-k", type=int, default=80000, help="仅扫描 AppID 最大的前K个（默认80000）")
    p.add_argument("--workers", type=int, default=6, help="并发数（默认6，建议4-8）")
    p.add_argument("--delay", type=float, default=0.6, help="每个请求基础延迟（默认0.6s，建议0.5-0.8）")
    p.add_argument("--batch-size", type=int, default=500, help="批大小（默认500）")
    p.add_argument("--progress-every", type=int, default=200, help="每处理多少条打印一次进度（默认200）")
    args = p.parse_args()

    logger.info("=" * 60)
    logger.info("Steam 高 AppID 未发布标签爬虫 启动")
    logger.info("=" * 60)

    run(args.categories, args.top_k, args.workers, args.delay, args.batch_size, args.progress_every)
    logger.info("完成！")


if __name__ == "__main__":
    main()
