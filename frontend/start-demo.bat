@echo off
REM Windows用户启动Demo模式的批处理文件

echo ========================================
echo 🎭 Steam游戏选择器 - Demo模式
echo ========================================
echo.

set VITE_DEMO_MODE=true

echo 正在启动开发服务器...
echo.

npm run dev

pause





