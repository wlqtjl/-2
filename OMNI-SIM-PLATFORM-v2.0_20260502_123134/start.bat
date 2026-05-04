@echo off
chcp 65001 >nul
echo ==========================================
echo    OMNI-SIM PLATFORM v2.0 启动脚本
echo ==========================================
echo.

REM 启动后端服务
echo 启动后端服务 (端口: 8000)...
cd backend
if exist "venv" (
    call venv\Scripts\activate.bat
) else (
    echo ⚠️ 虚拟环境不存在，请先运行 install.bat
)
start "后端服务" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
echo ✅ 后端服务已启动
cd ..

REM 等待后端启动
timeout /t 5 /nobreak >nul

REM 启动前端服务
echo.
echo 启动前端服务 (端口: 3002)...
cd frontend\apps\web
start "前端服务" cmd /k "npm run dev"
echo ✅ 前端服务已启动
cd ..\..\..

echo.
echo ==========================================
echo 服务已启动!
echo 前端地址: http://localhost:3002
echo 后端地址: http://localhost:8000
echo.
echo 按任意键关闭启动窗口
echo ==========================================
pause >nul