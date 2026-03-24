#!/bin/bash
# Obsidian 语义检索系统 - 一键启动脚本
# 使用方法: ./start.sh

set -e

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Obsidian 语义检索系统${NC}"
echo "================================"

# 初始化 conda
CONDA_BASE="/Users/liuwj77/miniconda3"
if [ ! -d "$CONDA_BASE" ]; then
    echo -e "${RED}❌ 未找到 miniconda，请修改脚本中的 CONDA_BASE 路径${NC}"
    exit 1
fi

source "$CONDA_BASE/etc/profile.d/conda.sh"

# 检查 conda 环境
if ! conda info --envs | grep -q "obsidian_rag"; then
    echo -e "${RED}❌ 未找到 obsidian_rag 环境，请先创建:${NC}"
    echo "   conda create -n obsidian_rag python=3.10 -y"
    echo "   conda activate obsidian_rag"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 激活环境
conda activate obsidian_rag

# 设置离线模式（使用缓存的模型）
export HF_HUB_OFFLINE=1

# 检查端口是否被占用
check_port() {
    if lsof -i :$1 >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $1 已被占用，尝试停止旧进程...${NC}"
        pkill -f "python -m backend.main" 2>/dev/null || true
        pkill -f "streamlit run ui" 2>/dev/null || true
        sleep 2
    fi
}

check_port 8000
check_port 8501

# 启动后端
echo -e "${GREEN}📡 启动后端服务...${NC}"
nohup python -m backend.main > backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
echo -e "${YELLOW}⏳ 等待模型加载（首次启动较慢）...${NC}"
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 后端服务已就绪${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ 后端启动超时，请检查 backend.log${NC}"
        exit 1
    fi
    sleep 1
done

# 启动 UI
echo -e "${GREEN}🖥️  启动 Web UI...${NC}"
nohup streamlit run ui/app.py --server.headless true > ui.log 2>&1 &
UI_PID=$!
echo "UI PID: $UI_PID"

# 等待 UI 启动
sleep 3
if curl -s http://127.0.0.1:8501 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Web UI 已就绪${NC}"
else
    echo -e "${YELLOW}⏳ UI 启动中，请稍候...${NC}"
fi

# 显示访问地址
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🚀 服务已启动！${NC}"
echo ""
echo -e "  ${YELLOW}Web UI:${NC}    http://localhost:8501"
echo -e "  ${YELLOW}API 文档:${NC}   http://localhost:8000/docs"
echo ""
echo -e "  ${YELLOW}日志文件:${NC}"
echo "    后端: $PROJECT_DIR/backend.log"
echo "    UI:   $PROJECT_DIR/ui.log"
echo ""
echo -e "  ${YELLOW}停止服务:${NC}   ./stop.sh"
echo -e "${GREEN}================================${NC}"

# 保存 PID 到文件
echo $BACKEND_PID > .backend.pid
echo $UI_PID > .ui.pid