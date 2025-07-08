#!/usr/bin/env python3
"""
Steam 游戏信息增强功能演示脚本
展示新增的功能：
1. 重复检测（potential_duplicate）
2. 游戏描述抓取
3. 发布时间获取
4. 支持语言列表
5. 价格信息（包括折扣）
"""

import requests
import json
from datetime import datetime, timezone
from steam_daily import (
    get_game_details, 
    find_similar_games, 
    normalize_game_name, 
    calculate_name_similarity,
    get_version_type
)

def demo_game_details():
    """演示游戏详细信息获取"""
    print("=== 游戏详细信息获取演示 ===\n")
    
    # 测试游戏列表
    test_games = [
        3809920,  # Wicked Little Witch
        3821130,  # Wicked Little Witch Demo
        1086940,  # Baldur's Gate 3 (作为对比)
        1245620,  # ELDEN RING (作为对比)
    ]
    
    session = requests.Session()
    games_data = []
    
    for appid in test_games:
        print(f"正在获取游戏 {appid} 的详细信息...")
        details = get_game_details(appid, session)
        
        if details:
            games_data.append(details)
            print(f"✓ 成功获取: {details.get('name', 'Unknown')}")
            print(f"  - 发布日期: {details.get('release_date', 'N/A')}")
            print(f"  - 支持语言: {', '.join(details.get('supported_languages', [])[:3])}...")
            print(f"  - 描述: {details.get('description', 'N/A')[:100]}...")
            print(f"  - 开发商: {', '.join(details.get('developers', []))}")
            print(f"  - 发行商: {', '.join(details.get('publishers', []))}")
            print(f"  - 网站: {details.get('website', 'N/A')}")
            print()
        else:
            print(f"✗ 无法获取游戏 {appid} 的信息")
            print()
    
    return games_data

def demo_duplicate_detection(games_data):
    """演示重复检测功能"""
    print("=== 重复检测功能演示 ===\n")
    
    if len(games_data) < 2:
        print("需要至少2个游戏来演示重复检测功能")
        return
    
    for i, game in enumerate(games_data):
        name = game.get('name', '')
        if not name:
            continue
            
        print(f"检查游戏: {name}")
        
        # 与其他游戏比较
        other_games = [g for j, g in enumerate(games_data) if j != i]
        similar_games = find_similar_games(name, other_games, threshold=0.8)
        
        if similar_games:
            print(f"  发现 {len(similar_games)} 个相似游戏:")
            for similar in similar_games:
                similarity = calculate_name_similarity(name, similar.get('name', ''))
                version_type = get_version_type(similar.get('name', ''))
                print(f"    - {similar.get('name', 'N/A')} (相似度: {similarity:.2f})")
                print(f"      版本类型: {version_type}")
                print(f"      开发商匹配: {'是' if game.get('developers') == similar.get('developers') else '否'}")
        else:
            print(f"  未发现相似游戏")
        print()

def demo_name_normalization():
    """演示名称标准化功能"""
    print("=== 名称标准化功能演示 ===\n")
    
    test_names = [
        "Wicked Little Witch",
        "Wicked Little Witch Demo",
        "Wicked Little Witch - Playtest",
        "WICKED LITTLE WITCH",
        "wicked little witch",
        "Wicked Little Witch™",
        "Wicked Little Witch (Beta)",
        "Baldur's Gate 3",
        "Baldur's Gate 3 - Early Access"
    ]
    
    for name in test_names:
        normalized = normalize_game_name(name)
        version_type = get_version_type(name)
        print(f"原始名称: {name}")
        print(f"标准化名称: {normalized}")
        print(f"版本类型: {version_type}")
        print()

def demo_similarity_calculation():
    """演示相似度计算功能"""
    print("=== 相似度计算功能演示 ===\n")
    
    base_name = "Wicked Little Witch"
    test_names = [
        "Wicked Little Witch Demo",
        "Wicked Little Witch Playtest",
        "Wicked Little Witch Beta",
        "Little Witch Academia",
        "Witch Hunt",
        "Completely Different Game",
        "The Witcher 3"
    ]
    
    print(f"基准游戏: {base_name}")
    print("与其他游戏的相似度:")
    
    for name in test_names:
        similarity = calculate_name_similarity(base_name, name)
        status = "可能重复" if similarity > 0.8 else "不同游戏"
        print(f"  {name}: {similarity:.3f} ({status})")
    print()

def main():
    """主函数"""
    print("Steam 游戏信息增强功能演示")
    print("=" * 50)
    print()
    
    # 1. 演示游戏详细信息获取
    games_data = demo_game_details()
    
    # 2. 演示重复检测功能
    demo_duplicate_detection(games_data)
    
    # 3. 演示名称标准化
    demo_name_normalization()
    
    # 4. 演示相似度计算
    demo_similarity_calculation()
    
    print("演示完成！")
    print("\n可用的新功能总结:")
    print("✓ 游戏描述抓取 - 快速了解游戏玩法")
    print("✓ 发布时间获取 - 跟踪游戏发布状态")
    print("✓ 支持语言列表 - 了解本地化情况")
    print("✓ 重复检测 - 识别Demo、Beta、Playtest等变体")
    print("✗ Wishlist数据 - Steam API不支持")
    print("✗ 用户标签 - Steam API不支持")

if __name__ == "__main__":
    main() 