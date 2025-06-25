#!/usr/bin/env python
"""
Steam游戏爬虫
每日抓取Steam新游戏信息
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from django.utils import timezone

# 添加Django项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'steam_project.settings')

import django
django.setup()

from games.models import Game


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SteamScraper:
    """Steam游戏爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Steam API URLs
        self.new_releases_url = "https://store.steampowered.com/api/featuredcategories"
        self.app_details_url = "https://store.steampowered.com/api/appdetails"
        self.search_url = "https://store.steampowered.com/search/results"
        
    def get_new_releases(self) -> List[Dict]:
        """获取Steam新发布的游戏"""
        try:
            logger.info("正在获取Steam新发布游戏...")
            response = self.session.get(self.new_releases_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            new_releases = []
            
            # 获取新发布和即将发布的游戏
            if 'new_releases' in data and 'items' in data['new_releases']:
                new_releases.extend(data['new_releases']['items'])
            
            if 'coming_soon' in data and 'items' in data['coming_soon']:
                new_releases.extend(data['coming_soon']['items'])
            
            logger.info(f"找到 {len(new_releases)} 个新游戏")
            return new_releases
            
        except Exception as e:
            logger.error(f"获取新游戏失败: {e}")
            return []
    
    def get_recent_games_by_search(self) -> List[Dict]:
        """通过搜索接口获取最近的游戏"""
        try:
            logger.info("正在通过搜索获取最近游戏...")
            
            # 搜索最近30天的游戏
            params = {
                'query': '',
                'sort_by': 'Released_DESC',  # 按发布日期降序
                'category1': '998',  # 游戏分类
                'snr': '1_7_7_230_7',
                'infinite': 1,
                'count': 50,  # 获取50个游戏
                'dynamic_data': '',
                'start': 0
            }
            
            response = self.session.get(self.search_url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析HTML响应（Steam搜索返回HTML片段）
            html_content = response.text
            
            # 简单的正则解析（在实际生产中建议使用BeautifulSoup）
            import re
            app_ids = re.findall(r'data-ds-appid="(\d+)"', html_content)
            
            games = []
            for app_id in app_ids[:20]:  # 限制数量
                game_info = {'id': app_id}
                games.append(game_info)
            
            logger.info(f"通过搜索找到 {len(games)} 个游戏")
            return games
            
        except Exception as e:
            logger.error(f"搜索游戏失败: {e}")
            return []
    
    def get_game_details(self, app_id: str) -> Optional[Dict]:
        """获取游戏详细信息"""
        try:
            params = {
                'appids': app_id,
                'l': 'english',  # 使用英文避免编码问题
                'cc': 'US'
            }
            
            response = self.session.get(self.app_details_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if app_id in data and data[app_id]['success']:
                return data[app_id]['data']
            else:
                logger.warning(f"游戏 {app_id} 信息获取失败")
                return None
                
        except Exception as e:
            logger.error(f"获取游戏 {app_id} 详情失败: {e}")
            return None
    
    def parse_game_data(self, game_data: Dict, app_id: str = None) -> Dict:
        """解析游戏数据"""
        try:
            # 如果是搜索结果，app_id可能在game_data中
            steam_id = app_id or game_data.get('id') or game_data.get('steam_appid')
            
            # 如果这是来自new_releases的简单数据，获取详细信息
            if 'name' in game_data and 'steam_appid' not in game_data:
                # 这是来自featuredcategories API的数据，需要获取详细信息
                details = self.get_game_details(str(steam_id))
                if details:
                    # 将价格信息从简单数据传递到详细数据
                    simple_data = game_data.copy()
                    game_data = details
                    # 如果详细信息中没有价格，使用简单数据中的价格
                    if not game_data.get('price_overview') and simple_data.get('final_price'):
                        game_data['price_overview'] = {
                            'currency': simple_data.get('currency', 'USD'),
                            'initial': simple_data.get('original_price', simple_data.get('final_price')),
                            'final': simple_data.get('final_price'),
                            'discount_percent': simple_data.get('discount_percent', 0)
                        }
                else:
                    return None
            
            # 解析价格信息
            price_info = game_data.get('price_overview', {})
            price = None
            currency = 'USD'
            discount_percent = 0
            is_free = game_data.get('is_free', False)
            
            if price_info:
                # Steam价格通常以分为单位，但有时已经是美元
                initial_price = price_info.get('initial', 0)
                if initial_price > 1000:  # 如果价格大于1000，可能是分为单位
                    price = Decimal(str(initial_price / 100))
                else:
                    price = Decimal(str(initial_price))
                currency = price_info.get('currency', 'USD')
                discount_percent = price_info.get('discount_percent', 0)
            elif is_free:
                price = Decimal('0.00')
            elif 'final_price' in game_data:
                # 来自featuredcategories的价格数据
                final_price = game_data.get('final_price', 0)
                original_price = game_data.get('original_price', final_price)
                if final_price > 1000:  # 价格以分为单位
                    price = Decimal(str(original_price / 100))
                else:
                    price = Decimal(str(original_price))
                currency = game_data.get('currency', 'USD')
                discount_percent = game_data.get('discount_percent', 0)
            
            # 解析发布日期
            release_date = None
            if game_data.get('release_date'):
                if isinstance(game_data['release_date'], dict):
                    date_str = game_data['release_date'].get('date')
                else:
                    date_str = game_data['release_date']
                
                if date_str:
                    try:
                        # 尝试解析不同的日期格式
                        for fmt in ['%b %d, %Y', '%d %b, %Y', '%Y-%m-%d', '%B %d, %Y']:
                            try:
                                release_date = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass
            
            # 解析截图
            screenshots = []
            if game_data.get('screenshots'):
                screenshots = [shot.get('path_full') for shot in game_data['screenshots'][:5]]
            
            # 解析标签
            tags = []
            if game_data.get('genres'):
                tags = [genre.get('description') for genre in game_data['genres']]
            
            # 解析平台
            platforms = []
            if game_data.get('platforms'):
                platform_data = game_data['platforms']
                if platform_data.get('windows'): platforms.append('Windows')
                if platform_data.get('mac'): platforms.append('Mac')
                if platform_data.get('linux'): platforms.append('Linux')
            
            # 解析语言
            languages = []
            if game_data.get('supported_languages'):
                lang_text = game_data['supported_languages']
                # 简单解析支持的语言
                if 'English' in lang_text:
                    languages.append('English')
                if 'Chinese' in lang_text or '中文' in lang_text or 'Simplified Chinese' in lang_text:
                    languages.append('Chinese')
                if 'Japanese' in lang_text:
                    languages.append('Japanese')
                if 'French' in lang_text:
                    languages.append('French')
                if 'German' in lang_text:
                    languages.append('German')
                if 'Spanish' in lang_text:
                    languages.append('Spanish')
            
            parsed_data = {
                'steam_id': str(steam_id),
                'name': game_data.get('name', ''),
                'description': game_data.get('short_description', ''),
                'price': price,
                'currency': currency,
                'discount_percent': discount_percent,
                'header_image': game_data.get('header_image', ''),
                'screenshots': screenshots,
                'developer': ', '.join(game_data.get('developers', [])),
                'publisher': ', '.join(game_data.get('publishers', [])),
                'release_date': release_date,
                'tags': tags,
                'platforms': platforms,
                'languages': languages,
                'is_free': is_free,
                'is_new': True,
                'scraped_at': timezone.now()
            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"解析游戏数据失败: {e}")
            return None
    
    def save_game(self, game_data: Dict) -> bool:
        """保存游戏到数据库"""
        try:
            steam_id = game_data['steam_id']
            
            # 检查游戏是否已存在
            existing_game = Game.objects.filter(steam_id=steam_id).first()
            
            if existing_game:
                # 更新现有游戏信息
                for key, value in game_data.items():
                    if key != 'steam_id':  # 不更新steam_id
                        setattr(existing_game, key, value)
                existing_game.save()
                logger.info(f"更新游戏: {game_data['name']}")
            else:
                # 创建新游戏
                Game.objects.create(**game_data)
                logger.info(f"新增游戏: {game_data['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"保存游戏失败: {e}")
            return False
    
    def run_scraper(self):
        """运行爬虫"""
        logger.info("开始Steam游戏爬虫任务")
        start_time = time.time()
        
        total_games = 0
        success_count = 0
        
        try:
            # 1. 获取新发布的游戏
            new_releases = self.get_new_releases()
            
            # 2. 获取搜索结果中的最近游戏
            recent_games = self.get_recent_games_by_search()
            
            # 合并游戏列表
            all_games = new_releases + recent_games
            
            # 去重
            seen_ids = set()
            unique_games = []
            for game in all_games:
                game_id = game.get('id') or game.get('steam_appid')
                if game_id and game_id not in seen_ids:
                    seen_ids.add(game_id)
                    unique_games.append(game)
            
            total_games = len(unique_games)
            logger.info(f"总共找到 {total_games} 个游戏待处理")
            
            # 3. 处理每个游戏
            for i, game in enumerate(unique_games, 1):
                try:
                    logger.info(f"处理第 {i}/{total_games} 个游戏")
                    
                    # 解析游戏数据
                    parsed_data = self.parse_game_data(game)
                    
                    if parsed_data:
                        # 保存到数据库
                        if self.save_game(parsed_data):
                            success_count += 1
                    
                    # 添加延迟避免被Steam限制
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"处理游戏失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"爬虫运行失败: {e}")
        
        # 统计信息
        elapsed_time = time.time() - start_time
        logger.info(f"爬虫任务完成")
        logger.info(f"处理时间: {elapsed_time:.2f}秒")
        logger.info(f"总游戏数: {total_games}")
        logger.info(f"成功处理: {success_count}")
        logger.info(f"失败数量: {total_games - success_count}")


def main():
    """主函数"""
    scraper = SteamScraper()
    scraper.run_scraper()


if __name__ == '__main__':
    main() 