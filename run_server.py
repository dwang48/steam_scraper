#!/usr/bin/env python3
"""
一键启动Django服务器的便捷脚本
"""

import os
import sys
import subprocess

def main():
    print("🎮 启动Steam游戏监控系统...")
    
    # 检查是否在正确的目录
    if not os.path.exists('backend/manage.py'):
        print("❌ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 进入backend目录
    os.chdir('backend')
    
    try:
        print("🚀 启动Django开发服务器...")
        print("📱 访问地址: http://127.0.0.1:8000")
        print("⏹️  按 Ctrl+C 停止服务器")
        print("-" * 40)
        
        # 启动Django服务器
        subprocess.run([sys.executable, 'manage.py', 'runserver'], check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
    except Exception as e:
        print(f"❌ 出现错误: {e}")

if __name__ == '__main__':
    main() 