#!/usr/bin/env python
"""
定时任务调度器
用于定时运行Steam爬虫
"""

import schedule
import time
import logging
from datetime import datetime
from steam_scraper import SteamScraper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_daily_scraper():
    """运行每日爬虫任务"""
    logger.info("开始执行每日Steam爬虫任务")
    try:
        scraper = SteamScraper()
        scraper.run_scraper()
        logger.info("每日爬虫任务完成")
    except Exception as e:
        logger.error(f"每日爬虫任务失败: {e}")


def main():
    """主调度函数"""
    logger.info("Steam爬虫调度器启动")
    
    # 设置每日定时任务 - 每天早上8点执行
    schedule.every().day.at("08:00").do(run_daily_scraper)
    
    # 也可以设置其他时间间隔，比如每小时执行一次
    # schedule.every().hour.do(run_daily_scraper)
    
    # 可以立即执行一次
    logger.info("立即执行一次爬虫任务")
    run_daily_scraper()
    
    # 开始调度循环
    logger.info("调度器开始运行，等待定时任务...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == '__main__':
    main() 