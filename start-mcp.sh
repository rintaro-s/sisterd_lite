#!/bin/bash
#
# systerd-lite MCP Server Launcher
# MCPサーバーをバックグラウンドで安定起動
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT=${1:-8089}
GRADIO_PORT=${2:-7861}
LOG_FILE="/tmp/systerd-lite.log"
PID_FILE="/tmp/systerd-lite.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo " systerd-lite MCP Server"
echo "========================================="

# Kill existing instances
echo -e "${YELLOW}Stopping existing instances...${NC}"
pkill -f "systerd-lite.py" 2>/dev/null || true
pkill -f "mcp_server_unified.py" 2>/dev/null || true
sleep 2

# Double check
if pgrep -f "systerd-lite.py" > /dev/null 2>&1; then
    echo -e "${RED}Failed to stop existing process, forcing...${NC}"
    pkill -9 -f "systerd-lite.py" 2>/dev/null || true
    sleep 1
fi

# Setup venv
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Install dependencies (quiet)
echo -e "${YELLOW}Checking dependencies...${NC}"
.venv/bin/pip install -q --upgrade pip 2>/dev/null
.venv/bin/pip install -q aiohttp psutil gradio numpy sympy requests 2>/dev/null || true

# Create state directory
mkdir -p .state

# Clear old log
> "$LOG_FILE"

# Start server in background with nohup
echo -e "${GREEN}Starting MCP server...${NC}"
nohup .venv/bin/python systerd-lite.py \
    --port "$PORT" \
    --gradio "$GRADIO_PORT" \
    >> "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo $NEW_PID > "$PID_FILE"

# Wait for server to start
echo -n "Waiting for server to start"
for i in {1..30}; do
    sleep 0.5
    echo -n "."
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ Server started successfully!${NC}"
        echo ""
        echo "  PID: $NEW_PID"
        echo "  HTTP API: http://localhost:$PORT"
        echo "  Gradio UI: http://localhost:$GRADIO_PORT"
        echo "  Log file: $LOG_FILE"
        echo ""
        echo "VS Code MCP config (.vscode/mcp.json):"
        echo '{'
        echo '  "servers": {'
        echo '    "systerd": {'
        echo '      "type": "http",'
        echo "      \"url\": \"http://localhost:$PORT\""
        echo '    }'
        echo '  }'
        echo '}'
        echo ""
        
        # Show tool count
        TOOLS=$(curl -s -X POST "http://localhost:$PORT/" \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' 2>/dev/null \
            | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(len(d.get('result',{}).get('tools',[])))" 2>/dev/null || echo "?")
        echo -e "${GREEN}Enabled tools: $TOOLS${NC}"
        exit 0
    fi
done

echo ""
echo -e "${RED}✗ Server failed to start!${NC}"
echo "Check log: $LOG_FILE"
echo ""
echo "Last 20 lines of log:"
tail -20 "$LOG_FILE"
exit 1
