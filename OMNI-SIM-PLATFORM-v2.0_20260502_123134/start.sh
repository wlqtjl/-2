#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "    OMNI-SIM PLATFORM v2.0 启动脚本"
echo "=========================================="
echo ""

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3002}"

# 启动后端服务
echo "启动后端服务 (端口: ${BACKEND_PORT})…"
cd backend
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "⚠️  虚拟环境不存在，请先运行 install.sh"
  exit 1
fi
uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!
echo "✅ 后端进程已拉起 (PID: $BACKEND_PID)"

FRONTEND_PID=""
cleanup() {
  echo ""
  echo "正在停止服务…"
  if kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" || true
  fi
  if [ -n "${FRONTEND_PID}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" || true
  fi
  exit 0
}
trap cleanup INT TERM

# 探测后端 readiness（依赖 /ready 健康检查）
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/ready" >/dev/null 2>&1; then
    echo "✅ 后端就绪 (${i}s)"
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "❌ 后端进程提前退出"
    exit 1
  fi
  sleep 1
  if [ "$i" = "60" ]; then
    echo "❌ 后端 60s 内未就绪，请查看日志"
    cleanup
  fi
done

# 启动前端服务
echo ""
echo "启动前端服务 (端口: ${FRONTEND_PORT})…"
cd ../frontend/apps/web
npm run dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!
echo "✅ 前端进程已拉起 (PID: $FRONTEND_PID)"

echo ""
echo "=========================================="
echo "服务已启动！"
echo "前端地址: http://localhost:${FRONTEND_PORT}"
echo "后端地址: http://localhost:${BACKEND_PORT}"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

wait
