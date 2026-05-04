@echo off
chcp 65001 >nul
echo ==========================================
echo    OMNI-SIM PLATFORM v2.0 安装脚本
echo ==========================================
echo.

REM 检查Python版本
echo [1/6] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请先安装Python
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

REM 创建虚拟环境
echo.
echo [2/6] 创建虚拟环境...
cd backend
if not exist "venv" (
    python -m venv venv
    echo ✅ 虚拟环境创建成功
) else (
    echo ⚠️ 虚拟环境已存在
)

REM 激活虚拟环境并安装依赖
echo.
echo [3/6] 安装后端依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo ✅ 后端依赖安装完成

REM 安装前端依赖
echo.
echo [4/6] 安装前端依赖...
cd ..\frontend\apps\web
if not exist "node_modules" (
    npm install -q
    echo ✅ 前端依赖安装完成
) else (
    echo ⚠️ 前端依赖已存在
)

REM 返回项目根目录
cd ..\..\..

REM 创建.env文件（如果不存在）
echo.
echo [5/6] 检查配置文件...
if not exist "backend\.env" (
    (
        echo # OMNI-SIM PLATFORM v2.0 配置文件
        echo.
        echo # 数据库配置
        echo USE_SQLITE=true
        echo POSTGRES_USER=admin
        echo POSTGRES_PASSWORD=password
        echo POSTGRES_DB=game_training
        echo POSTGRES_HOST=localhost
        echo POSTGRES_PORT=5432
        echo.
        echo # JWT配置
        echo SECRET_KEY=dev-secret-key-change-in-production
        echo ALGORITHM=HS256
        echo ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo.
        echo # AI配置
        echo CLAUDE_API_KEY=
        echo CLAUDE_API_URL=https://api.anthropic.com/v1/messages
        echo CLAUDE_MODEL=claude-3-sonnet-20240229
        echo.
        echo QIANWEN_API_KEY=
        echo QIANWEN_API_URL=https://dashscope.aliyuncs.com/api/text/generation
        echo QIANWEN_MODEL=qwen-turbo
        echo.
        echo DEEPSEEK_API_KEY=
        echo DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
        echo DEEPSEEK_MODEL=deepseek-chat
        echo.
        echo DEFAULT_AI_MODEL=deepseek
        echo.
        echo # 应用配置
        echo APP_NAME=游戏化培训平台 2.0
        echo APP_ENV=development
        echo APP_PORT=8000
    ) > backend\.env
    echo ✅ 配置文件创建成功
) else (
    echo ⚠️ 配置文件已存在
)

echo.
echo [6/6] 创建启动脚本...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo echo ==========================================
    echo echo    OMNI-SIM PLATFORM v2.0 启动脚本
    echo echo ==========================================
    echo echo.
    echo.
    echo REM 启动后端服务
    echo echo 启动后端服务 ^(端口: 8000^)...
    echo cd backend
    echo call venv\Scripts\activate.bat
    echo start "后端服务" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
    echo echo ✅ 后端服务已启动
    echo cd ..
    echo.
    echo REM 等待后端启动
    echo timeout /t 5 /nobreak ^>nul
    echo.
    echo REM 启动前端服务
    echo echo 启动前端服务 ^(端口: 3002^)...
    echo cd frontend\apps\web
    echo start "前端服务" cmd /k "npm run dev"
    echo echo ✅ 前端服务已启动
    echo cd ..\..\..
    echo.
    echo echo ==========================================
    echo echo 服务已启动^!
    echo echo 前端地址: http://localhost:3002
    echo echo 后端地址: http://localhost:8000
    echo echo.
    echo echo 按任意键关闭启动窗口
    echo echo ==========================================
    echo pause ^>nul
) > start.bat
echo ✅ 启动脚本创建成功

echo.
echo ==========================================
echo 安装完成^!
echo.
echo 使用方法:
echo   1. 运行启动脚本: start.bat
echo   2. 访问前端: http://localhost:3002
echo   3. 访问后端API: http://localhost:8000
echo.
echo 默认测试账号:
echo   邮箱: 137151453@qq.com
echo   密码: wlqtjl123
echo ==========================================
pause