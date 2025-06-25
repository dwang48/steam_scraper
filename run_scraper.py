#!/usr/bin/env python3
"""
一键运行Steam爬虫的便捷脚本
"""

import os
import sys

def main():
    print("🕷️ 启动Steam游戏爬虫...")
    
    # 检查是否在正确的目录
    if not os.path.exists('scraper/steam_scraper.py'):
        print("❌ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    try:
        # 导入并运行爬虫
        sys.path.append('scraper')
        from scraper.steam_scraper import main as run_scraper
        
        print("🎯 开始抓取Steam游戏数据...")
        print("📊 这可能需要几分钟时间，请耐心等待...")
        print("-" * 40)
        
        run_scraper()
        
        print("\n✅ 爬虫任务完成！")
        print("🌐 现在可以访问 http://127.0.0.1:8000 查看结果")
        
    except KeyboardInterrupt:
        print("\n\n🛑 爬虫任务已中断")
    except Exception as e:
        print(f"❌ 爬虫运行失败: {e}")
        print("💡 请确保:")
        print("   1. 已安装所有依赖: pip install -r requirements.txt")
        print("   2. 已初始化数据库: cd backend && python manage.py migrate")
        print("   3. 网络连接正常")

if __name__ == '__main__':
    main() 