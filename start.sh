#!/bin/bash

echo "🎮 Steam游戏爬虫MVP启动脚本"
echo "================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: 未找到pip3，请先安装pip3"
    exit 1
fi

echo "📦 安装Python依赖..."
pip3 install -r requirements.txt

echo "🔧 初始化Django数据库..."
cd backend
python3 manage.py makemigrations
python3 manage.py migrate

echo "👤 创建超级用户（可选，用于管理界面）..."
echo "是否要创建Django超级用户？(y/n)"
read -r create_superuser
if [[ $create_superuser == "y" || $create_superuser == "Y" ]]; then
    python3 manage.py createsuperuser
fi

echo ""
echo "🚀 项目设置完成！"
echo ""
echo "📋 使用说明："
echo "1. 启动Django服务器: cd backend && python3 manage.py runserver"
echo "2. 运行爬虫: python3 scraper/steam_scraper.py"
echo "3. 启动定时爬虫: python3 scraper/scheduler.py"
echo ""
echo "🌐 访问地址："
echo "- 前端页面: http://127.0.0.1:8000"
echo "- API接口: http://127.0.0.1:8000/api/"
echo "- 管理界面: http://127.0.0.1:8000/admin/"
echo ""
echo "💡 建议："
echo "- 首次使用请先运行一次爬虫来获取游戏数据"
echo "- 可以在管理界面查看和管理游戏数据"
echo "- 修改scraper/scheduler.py中的定时设置来调整爬取频率" 