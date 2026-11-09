#!/bin/bash
# ============================================
# File Transfer 服务守护脚本
# 用于 DolphinScheduler 定时任务 / Crontab 守护
# ============================================

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SCRIPT="app.py"

# Python 解释器自动探测：环境变量指定优先 -> Conda 环境优先 -> 系统 python3
if [ -n "${PYTHON_BIN:-}" ] && [ -x "$PYTHON_BIN" ]; then
    PYTHON_EXEC="$PYTHON_BIN"
elif [ -x "/home/charlie/miniconda3/bin/python3" ]; then
    PYTHON_EXEC="/home/charlie/miniconda3/bin/python3"
elif [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python3" ]; then
    PYTHON_EXEC="$CONDA_PREFIX/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="$(command -v python3)"
else
    echo "❌ [$(date)] 未找到可用的 Python3 环境"
    exit 1
fi

PORT="${PORT:-18000}"
LOG_FILE="$APP_DIR/app.log"
PID_FILE="$APP_DIR/app.pid"

cd "$APP_DIR" || { echo "❌ 目录不存在: $APP_DIR"; exit 1; }

# 检查服务是否存活（通过端口检测）
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo "✅ [$(date)] 服务正常运行中 (端口 $PORT 已监听)"
    PID=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1)
    echo "   PID: $PID"
    exit 0
fi

echo "⚠️  [$(date)] 服务未运行，正在启动..."

# 清理残留端口
fuser -k "${PORT}/tcp" 2>/dev/null
[ -f "$PID_FILE" ] && rm -f "$PID_FILE"

# 后台启动（SETSID 脱离当前 session）
"$PYTHON_EXEC" -c "
import subprocess, os
os.chdir('$APP_DIR')
with open('$LOG_FILE', 'a') as f:
    p = subprocess.Popen(['$PYTHON_EXEC', '$APP_SCRIPT'], stdout=f, stderr=f, start_new_session=True)
    with open('$PID_FILE', 'w') as pf:
        pf.write(str(p.pid))
"

# 等待 3 秒后验证
sleep 3

if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    NEW_PID=$(cat "$PID_FILE" 2>/dev/null)
    echo "✅ [$(date)] 服务启动成功！PID: $NEW_PID"
    tail -5 "$LOG_FILE"
    exit 0
else
    echo "❌ [$(date)] 服务启动失败！最近日志:"
    tail -20 "$LOG_FILE"
    exit 1
fi
