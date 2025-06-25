#!/usr/bin/env python3
"""
创建演示数据的脚本
用于快速展示系统功能
"""

import os
import sys
import django
from datetime import datetime, date
from decimal import Decimal

# 设置Django环境
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'steam_project.settings')
django.setup()

from games.models import Game

def create_demo_games():
    """创建演示游戏数据"""
    
    demo_games = [
        {
            'steam_id': '1245620',
            'name': 'ELDEN RING',
            'description': '探索广袤的奇幻世界，体验史诗般的冒险',
            'price': Decimal('59.99'),
            'currency': 'USD',
            'discount_percent': 20,
            'header_image': 'https://cdn.akamai.steamstatic.com/steam/apps/1245620/header.jpg',
            'developer': 'FromSoftware Inc.',
            'publisher': 'Bandai Namco Entertainment',
            'release_date': date(2022, 2, 25),
            'tags': ['动作', 'RPG', '开放世界', '黑暗奇幻'],
            'platforms': ['Windows', 'PlayStation', 'Xbox'],
            'languages': ['English', 'Japanese', 'Chinese'],
            'is_free': False,
            'is_new': True,
            'review_score': 96
        },
        {
            'steam_id': '1888930',
            'name': 'Baldur\'s Gate 3',
            'description': '基于龙与地下城规则的回合制RPG巨作',
            'price': Decimal('59.99'),
            'currency': 'USD',
            'discount_percent': 0,
            'header_image': 'https://cdn.akamai.steamstatic.com/steam/apps/1086940/header.jpg',
            'developer': 'Larian Studios',
            'publisher': 'Larian Studios',
            'release_date': date(2023, 8, 3),
            'tags': ['RPG', '策略', '多人游戏', '奇幻'],
            'platforms': ['Windows', 'Mac', 'PlayStation'],
            'languages': ['English', 'French', 'German'],
            'is_free': False,
            'is_new': True,
            'review_score': 96
        },
        {
            'steam_id': '1623730',
            'name': 'Palworld',
            'description': '收集帕尔，建设基地，在开放世界中冒险',
            'price': Decimal('29.99'),
            'currency': 'USD',
            'discount_percent': 15,
            'header_image': 'https://cdn.akamai.steamstatic.com/steam/apps/1623730/header.jpg',
            'developer': 'Pocketpair',
            'publisher': 'Pocketpair',
            'release_date': date(2024, 1, 19),
            'tags': ['生存', '制作', '开放世界', '多人游戏'],
            'platforms': ['Windows', 'Xbox'],
            'languages': ['English', 'Japanese', 'Chinese'],
            'is_free': False,
            'is_new': True,
            'review_score': 78
        },
        {
            'steam_id': '1517290',
            'name': 'Battlefield 2042',
            'description': '大规模多人射击游戏，体验未来战场',
            'price': Decimal('0.00'),
            'currency': 'USD',
            'discount_percent': 0,
            'header_image': 'https://cdn.akamai.steamstatic.com/steam/apps/1517290/header.jpg',
            'developer': 'DICE',
            'publisher': 'Electronic Arts',
            'release_date': date(2021, 11, 19),
            'tags': ['射击', '多人游戏', '战争', '动作'],
            'platforms': ['Windows', 'PlayStation', 'Xbox'],
            'languages': ['English', 'French', 'Spanish'],
            'is_free': True,
            'is_new': False,
            'review_score': 65
        },
        {
            'steam_id': '1938090',
            'name': 'Call of Duty®: Modern Warfare® III',
            'description': '经典系列的最新作品，重新定义现代战争',
            'price': Decimal('69.99'),
            'currency': 'USD',
            'discount_percent': 30,
            'header_image': 'https://cdn.akamai.steamstatic.com/steam/apps/1938090/header.jpg',
            'developer': 'Sledgehammer Games',
            'publisher': 'Activision',
            'release_date': date(2023, 11, 10),
            'tags': ['射击', '多人游戏', '战役', '竞技'],
            'platforms': ['Windows', 'PlayStation', 'Xbox'],
            'languages': ['English', 'Spanish', 'French'],
            'is_free': False,
            'is_new': True,
            'review_score': 71
        }
    ]
    
    created_count = 0
    
    for game_data in demo_games:
        # 检查游戏是否已存在
        if not Game.objects.filter(steam_id=game_data['steam_id']).exists():
            Game.objects.create(**game_data)
            created_count += 1
            print(f"✅ 创建游戏: {game_data['name']}")
        else:
            print(f"⚠️  游戏已存在: {game_data['name']}")
    
    print(f"\n🎉 演示数据创建完成！共创建 {created_count} 个游戏")
    return created_count

def main():
    print("🎮 创建Steam游戏演示数据")
    print("=" * 30)
    
    try:
        create_demo_games()
        print("\n💡 提示:")
        print("- 启动服务器: python3 run_server.py")
        print("- 访问页面: http://127.0.0.1:8000")
        print("- 管理界面: http://127.0.0.1:8000/admin/")
        
    except Exception as e:
        print(f"❌ 创建演示数据失败: {e}")
        print("💡 请确保已运行 Django 数据库迁移:")
        print("   cd backend && python3 manage.py migrate")

if __name__ == '__main__':
    main() 