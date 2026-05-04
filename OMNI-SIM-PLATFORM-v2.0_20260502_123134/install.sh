#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "    OMNI-SIM PLATFORM v2.0 安装脚本"
echo "=========================================="
echo ""

# 检查Python版本 (要求 >=3.9)
echo "[1/5] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3，请先安装Python 3.9+"
    exit 1
fi

PY_MAJOR=$(python3 -c 'import sys;print(sys.version_info[0])')
PY_MINOR=$(python3 -c 'import sys;print(sys.version_info[1])')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "❌ Python 版本为 ${PY_MAJOR}.${PY_MINOR}，需 ≥ 3.9。请升级后重试。"
    exit 1
fi
echo "✅ Python版本: ${PY_MAJOR}.${PY_MINOR}"

# 创建虚拟环境
echo ""
echo "[2/5] 创建虚拟环境..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "⚠️  虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo ""
echo "[3/5] 安装后端依赖..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ 后端依赖安装完成"

# 安装前端依赖
echo ""
echo "[4/5] 安装前端依赖..."
cd ../frontend/apps/web
if [ ! -d "node_modules" ]; then
    npm install -q
    echo "✅ 前端依赖安装完成"
else
    echo "⚠️  前端依赖已存在"
fi

# 返回项目根目录
cd ../../../

# 创建.env文件（如果不存在）
echo ""
echo "[5/5] 检查配置文件..."
if [ ! -f "backend/.env" ]; then
    # 生成随机 SECRET_KEY，避免默认 dev key上生产
    SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')
    cat > backend/.env <<EOF
# OMNI-SIM PLATFORM v2.0 配置文件

# 数据库配置
USE_SQLITE=true
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
POSTGRES_DB=game_training
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# JWT配置
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI配置
CLAUDE_API_KEY=
CLAUDE_API_URL=https://api.anthropic.com/v1/messages
CLAUDE_MODEL=claude-3-sonnet-20240229

QIANWEN_API_KEY=
QIANWEN_API_URL=https://dashscope.aliyuncs.com/api/text/generation
QIANWEN_MODEL=qwen-turbo

DEEPSEEK_API_KEY=
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_MODEL=deepseek-chat

DEFAULT_AI_MODEL=deepseek

# 应用配置
APP_NAME=游戏化培训平台 2.0
APP_ENV=development
APP_PORT=8000

# 前端可访问的 CORS 白名单
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3002
EOF
    echo "✅ 配置文件创建成功（已生成随机 SECRET_KEY）"
else
    echo "⚠️  配置文件已存在，跳过"
fi

chmod +x start.sh 2>/dev/null || true

echo ""
echo "=========================================="
echo "安装完成！"
echo ""
echo "使用方法:"
echo "  1. 运行启动脚本: ./start.sh"
echo "  2. 访问前端: http://localhost:3002"
echo "  3. 访问后端 API 文档: http://localhost:8000/docs"
echo ""
echo "首次启动后，请通过 /auth/register 创建账号，"
echo "或在数据库中导入种子数据。请勿在安装脚本中硕编凭据。"
echo "=========================================="
