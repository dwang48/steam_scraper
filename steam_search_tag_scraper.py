#!/usr/bin/env python3
"""
Steam 搜索版标签爬虫（高效、低限流）
- 通过 Steam 搜索接口按页抓取 Coming Soon 列表（category1=998=game）
- 在搜索结果页面级过滤标签文本，先收集候选，再对命中项做有限的 appdetails 补充
- 一次性支持多个分类（narrative / emotional / co-op / cozy）

用法示例：
  python steam_search_tag_scraper.py --categories narrative co-op cozy emotional --delay 0.75 --max-workers 4
  python steam_search_tag_scraper.py --categories narrative --max-pages 200 --delay 0.5
  python steam_search_tag_scraper.py --categories co-op --no-enrich  # 仅导出基础信息（更快）

生成 CSV 到 exports/，可配合 generate_excel_reports.py 生成 Excel。
"""

import os
import re
import csv
import json
import time
import html
import argparse
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# 目录
BASE_DIR = Path(__file__).parent
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# 搜索接口（无限滚动 JSON）
SEARCH_RESULTS_URL = (
    "https://store.steampowered.com/search/results/"
)

# 请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# 目标分类与匹配标签（基于搜索结果展示出来的标签文本做包含匹配）
TAG_CATEGORIES: Dict[str, List[str]] = {
    "narrative": ["Story Rich", "Narrative", "Interactive Fiction", "Visual Novel", "Text-Based"],
    "emotional": ["Emotional", "Drama", "Psychological", "Atmospheric", "Choices", "Character"],
    "co-op": ["Co-op", "Online Co-Op", "Local Co-Op", "Cooperative"],
    "cozy": ["Cozy", "Relaxing", "Wholesome", "Casual", "Peaceful", "Zen", "Family Friendly"],
}

FIELDS = [
    "name",
    "steam_appid",
    "steam_url",
    "release_date",
    "coming_soon",
    "tags_shown",        # 搜索结果中展示的标签文本（有限）
    "tag_category",
    # 以下字段仅在 enrich 时补充
    "developers",
    "publishers",
    "genres",
    "categories",
    "description",
    "supported_languages",
    "website",
    "discovery_date",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("steam_search_tag")

@dataclass
class SearchItem:
    appid: str
    name: str
    url: str
    release_date_text: str
    tags_shown: List[str]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_search_page(start: int, count: int, delay: float, session: requests.Session) -> Tuple[str, int]:
    """请求搜索接口一页数据，返回 (results_html, total_count)。"""
    params = {
        "query": "",              # 空查询
        "force_infinite": 1,
        "infinite": 1,
        "start": start,
        "count": count,
        "cc": "us",
        "l": "en",
        "category1": 998,         # 仅 game
        "filter": "comingsoon",  # 仅未发布（Coming Soon）
        # 可按需添加排序："sort_by": "Price_ASC" 等
    }
    time.sleep(delay)
    resp = session.get(SEARCH_RESULTS_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
    # 速率限制处理
    if resp.status_code == 429:
        logger.warning("Rate limited by search endpoint, sleeping 30s…")
        time.sleep(30)
        resp = session.get(SEARCH_RESULTS_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results_html", ""), int(data.get("total_count", 0))


def parse_results_html(results_html: str) -> List[SearchItem]:
    """从 results_html 解析出条目（appid、name、url、release、tags_shown）。"""
    items: List[SearchItem] = []
    if not results_html:
        return items
    soup = BeautifulSoup(results_html, "lxml")
    for a in soup.select("a.search_result_row"):
        appid = a.get("data-ds-appid") or ""
        if not appid:
            # 可能是 bundle/dlc
            ds_packageid = a.get("data-ds-packageid")
            if ds_packageid:
                continue
            # 尝试从 href 提取
            href = a.get("href", "")
            m = re.search(r"/app/(\d+)/", href)
            if m:
                appid = m.group(1)
        if not appid:
            continue
        name_el = a.select_one("span.title")
        name = clean_text(name_el.text) if name_el else ""
        href = a.get("href", "").split("?")[0]
        # 发售信息（文本）
        rd_el = a.select_one("div.search_released")
        release_date_text = clean_text(rd_el.text) if rd_el else ""
        # 展示标签（有限个）
        tags_el = a.select("div.search_tags span")
        tags_shown = [clean_text(t.text) for t in tags_el if clean_text(t.text)]
        items.append(SearchItem(appid=appid, name=name, url=href, release_date_text=release_date_text, tags_shown=tags_shown))
    return items


def match_category(tags_shown: List[str], category: str) -> bool:
    if not tags_shown:
        return False
    targets = TAG_CATEGORIES.get(category, [])
    tags_lower = [t.lower() for t in tags_shown]
    for target in targets:
        tl = target.lower()
        if any(tl in tag or tag in tl for tag in tags_lower):
            return True
    return False


def enrich_appdetails(appid: int, session: requests.Session, delay: float) -> Dict:
    """有限制地补充详情，避免被限流。"""
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
    time.sleep(delay)
    try:
        resp = session.get(url, headers=DEFAULT_HEADERS, timeout=20)
        if resp.status_code == 429:
            time.sleep(5)
            resp = session.get(url, headers=DEFAULT_HEADERS, timeout=20)
        if resp.status_code == 403:
            return {}
        resp.raise_for_status()
        data = resp.json().get(str(appid), {})
        if not data.get("success"):
            return {}
        d = data.get("data", {}) or {}
        # 仅提取需要的字段
        developers = ";".join(d.get("developers", []) or []) or None
        publishers = ";".join(d.get("publishers", []) or []) or None
        genres = ";".join([g.get("description", "") for g in (d.get("genres", []) or []) if g.get("description")]) or None
        categories = ";".join([c.get("description", "") for c in (d.get("categories", []) or []) if c.get("description")]) or None
        desc = d.get("short_description") or ""
        desc = clean_text(desc)
        langs = d.get("supported_languages") or ""
        if langs:
            # 粗略提取语言名（去掉 HTML）
            langs = clean_text(re.sub(r"<[^>]+>", " ", langs))
        website = d.get("website") or None
        # coming_soon 由搜索接口已过滤，这里不再决定逻辑，仅回填更标准的日期
        release_date = d.get("release_date", {})
        release_text = release_date.get("date") or None
        return {
            "developers": developers,
            "publishers": publishers,
            "genres": genres,
            "categories": categories,
            "description": desc or None,
            "supported_languages": langs or None,
            "website": website,
            "release_date_enriched": release_text,
        }
    except Exception:
        return {}


def export_csv(rows: List[Dict], category: str) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = EXPORT_DIR / f"steam_search_{category}_unreleased_{today}.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return out_path


def run_for_categories(categories: List[str], delay: float, page_size: int, max_pages: Optional[int], enrich: bool, max_workers: int, enrich_delay: float) -> Dict[str, List[Dict]]:
    session = requests.Session()
    results_by_cat: Dict[str, List[Dict]] = {}

    try:
        # 先获取第一页，拿 total_count（注意 total_count 可能很大）
        html0, total_count = fetch_search_page(start=0, count=page_size, delay=delay, session=session)
        if total_count <= 0:
            logger.warning("搜索接口返回 total_count=0，可能被限流或页面结构变更")
        # 从 0 开始分页
        pages = (total_count + page_size - 1) // page_size if total_count else (max_pages or 1)
        if max_pages is not None:
            pages = min(pages, max_pages)
        logger.info(f"预计抓取页数: {pages}（每页 {page_size} 条）")

        # 预处理首页
        page_items = parse_results_html(html0)
        all_pages_cache = {0: page_items}

        # 逐页抓取
        for page_idx in range(pages):
            start = page_idx * page_size
            if page_idx == 0:
                items = all_pages_cache[0]
            else:
                html, _ = fetch_search_page(start=start, count=page_size, delay=delay, session=session)
                items = parse_results_html(html)
            if not items:
                continue

            for cat in categories:
                matched: List[Dict] = results_by_cat.setdefault(cat, [])
                for it in items:
                    if match_category(it.tags_shown, cat):
                        matched.append({
                            "name": it.name,
                            "steam_appid": it.appid,
                            "steam_url": it.url,
                            "release_date": it.release_date_text,
                            "coming_soon": True,
                            "tags_shown": ";".join(it.tags_shown) if it.tags_shown else None,
                            "tag_category": cat,
                            "developers": None,
                            "publishers": None,
                            "genres": None,
                            "categories": None,
                            "description": None,
                            "supported_languages": None,
                            "website": None,
                            "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        })

        # 去重（同一 app 可能多页出现）
        for cat in categories:
            seen: Set[str] = set()
            deduped: List[Dict] = []
            for r in results_by_cat.get(cat, []):
                if r["steam_appid"] in seen:
                    continue
                seen.add(r["steam_appid"])
                deduped.append(r)
            results_by_cat[cat] = deduped
            logger.info(f"{cat}: 页面级匹配 {len(deduped)} 个候选")

        # 可选 enrich（有限并发 + 延时）
        if enrich:
            for cat in categories:
                rows = results_by_cat.get(cat, [])
                if not rows:
                    continue
                logger.info(f"{cat}: 开始补充详情（{len(rows)} 个）…")
                def task(row: Dict) -> Tuple[str, Dict]:
                    a = int(row["steam_appid"])
                    d = enrich_appdetails(a, session, enrich_delay)
                    return row["steam_appid"], d
                with ThreadPoolExecutor(max_workers=max_workers) as exe:
                    futures = {exe.submit(task, row): row for row in rows}
                    for fut in as_completed(futures):
                        row = futures[fut]
                        try:
                            _, detail = fut.result()
                            if detail:
                                # 合并字段
                                row.update({
                                    "developers": detail.get("developers"),
                                    "publishers": detail.get("publishers"),
                                    "genres": detail.get("genres"),
                                    "categories": detail.get("categories"),
                                    "description": detail.get("description"),
                                    "supported_languages": detail.get("supported_languages"),
                                    "website": detail.get("website"),
                                })
                                # 若 enrich 获得了更准确的日期则覆盖
                                if detail.get("release_date_enriched"):
                                    row["release_date"] = detail["release_date_enriched"]
                        except Exception:
                            pass

        # 导出 CSV
        for cat in categories:
            out = export_csv(results_by_cat.get(cat, []), cat)
            logger.info(f"导出 {cat}: {out}")

    finally:
        session.close()

    return results_by_cat


def main():
    parser = argparse.ArgumentParser(description="Steam 搜索版未发布标签爬虫（高效版）")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(TAG_CATEGORIES.keys()),
        required=True,
        help="要抓取的标签分类，可多选"
    )
    parser.add_argument("--delay", type=float, default=0.75, help="每页请求的基础延时（秒）")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量，建议 50")
    parser.add_argument("--max-pages", type=int, help="最多抓取的页数（不填则抓取全部页）")
    parser.add_argument("--no-enrich", action="store_true", help="不补充 appdetails 详情，速度更快")
    parser.add_argument("--max-workers", type=int, default=4, help="enrich 阶段的并发度（建议 2-6）")
    parser.add_argument("--enrich-delay", type=float, default=0.5, help="单个 appdetails 请求之间的延时（秒）")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Steam 搜索版未发布标签爬虫 启动")
    logger.info("=" * 60)

    enrich = not args.no_enrich
    run_for_categories(
        categories=args.categories,
        delay=args.delay,
        page_size=args.page_size,
        max_pages=args.max_pages,
        enrich=enrich,
        max_workers=args.max_workers,
        enrich_delay=args.enrich_delay,
    )

    logger.info("完成！")


if __name__ == "__main__":
    main()





