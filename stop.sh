#!/bin/bash
# Obsidian 语义检索系统 - 停止脚本
# 使用方法: ./stop.sh

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 停止服务...${NC}"

# 停止后端
if [ -f .backend.pid ]; then
    kill $(cat .backend.pid) 2>/dev/null || true
    rm .backend.pid
fi
pkill -f "python -m backend.main" 2>/dev/null || true

# 停止 UI
if [ -f .ui.pid ]; then
    kill $(cat .ui.pid) 2>/dev/null || true
    rm .ui.pid
fi
pkill -f "streamlit run ui" 2>/dev/null || true

sleep 1

echo -e "${GREEN}✅ 服务已停止${NC}"