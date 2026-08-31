#!/bin/bash
# 本地预览 docs/ 站点：./serve.sh [port]（默认 8000）
PORT=${1:-8000}
cd "$(dirname "$0")/docs" && python3 -m http.server "$PORT"
