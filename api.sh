#!/bin/bash
# 启动自索引 API 后端 + 静态站：./api.sh [port]（默认 8787）
cd "$(dirname "$0")"
exec .venv/bin/python server/api_server.py "${1:-8787}"
