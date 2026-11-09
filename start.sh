#!/bin/bash
# ==============================================================================
# start.sh – 一键启动 File Transfer 服务
# 自动探测 Python 环境 (venv / Conda / 系统 python3)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/file_transfer"
PORT="${PORT:-18000}"
HOST="${HOST:-0.0.0.0}"

# 1. 动态探测 Python 执行环境
if [ -n "${PYTHON_BIN:-}" ] && [ -x "$PYTHON_BIN" ]; then
    PYTHON_EXEC="$PYTHON_BIN"
elif [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    PYTHON_EXEC="$SCRIPT_DIR/venv/bin/python3"
elif [ -f "$APP_DIR/venv/bin/python3" ]; then
    PYTHON_EXEC="$APP_DIR/venv/bin/python3"
elif [ -n "${CONDA_PREFIX:-}" ] && [ -f "$CONDA_PREFIX/bin/python3" ]; then
    PYTHON_EXEC="$CONDA_PREFIX/bin/python3"
elif [ -x "/home/charlie/miniconda3/bin/python3" ]; then
    PYTHON_EXEC="/home/charlie/miniconda3/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="$(command -v python3)"
else
    echo "❌ 未检测到可用的 Python3 环境，请先安装 Python 或配置虚拟环境"
    exit 1
fi

echo "=================================================="
echo "  🚀 File Transfer 文件传输服务"
echo "  Python 环境: $("$PYTHON_EXEC" --version 2>&1) ($PYTHON_EXEC)"
echo "  监听地址: $HOST:$PORT"
echo "=================================================="

# 2. 检查 users.json 是否存在
if [ ! -f "$APP_DIR/users.json" ]; then
    echo "⚠️  未检测到 $APP_DIR/users.json 用户配置文件！"
    echo "   正在生成默认模板 (或可使用 python file_transfer/manage_users.py 创建账号)..."
    if [ -f "$APP_DIR/users.example.json" ]; then
        cp "$APP_DIR/users.example.json" "$APP_DIR/users.json"
        echo "   已从 users.example.json 复制初始化配置。"
    fi
fi

INNER_IP=$(ip route get 1 2>/dev/null | awk '{print $7}' | head -1 || hostname -I | awk '{print $1}' || echo "127.0.0.1")
echo ""
echo "  ✅ 服务即将启动，浏览器访问地址："
echo "       本地访问: http://127.0.0.1:${PORT}"
echo "       内网访问: http://${INNER_IP}:${PORT}"
echo ""

cd "$APP_DIR"
exec "$PYTHON_EXEC" app.py
