#!/bin/bash
#
# systerd-lite One-Command Launcher
# すべての機能を1コマンドで起動
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo " systerd-lite Launcher"
echo "========================================="
echo

# Check Python
if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv .venv
fi

# Install dependencies
echo "📦 Installing dependencies..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q aiohttp psutil dbus-next gradio numpy sympy requests 2>/dev/null || true

# Check Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker detected"
    DOCKER_AVAILABLE=1
else
    echo "⚠️  Docker not found - container features will be limited"
    DOCKER_AVAILABLE=0
fi

# Parse arguments
PORT=8089
GRADIO_PORT=7861
NO_UI=false
DEBUG=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --gradio)
            GRADIO_PORT="$2"
            shift 2
            ;;
        --no-ui)
            NO_UI=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --port PORT        HTTP API port (default: 8888)"
            echo "  --gradio PORT      Gradio UI port (default: 7860)"
            echo "  --no-ui            Disable Gradio UI"
            echo "  --debug            Enable debug logging"
            echo "  --help, -h         Show this help"
            echo
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Create state directory
mkdir -p .state

# Kill existing instance
pkill -f "systerd-lite.py" 2>/dev/null || true
sleep 1

# Build command
CMD=".venv/bin/python systerd-lite.py --port $PORT"

if [ "$NO_UI" = true ]; then
    CMD="$CMD --no-ui"
else
    CMD="$CMD --gradio $GRADIO_PORT"
fi

if [ "$DEBUG" = true ]; then
    CMD="$CMD --debug"
fi

# Show info
echo
echo "🚀 Starting systerd-lite..."
echo "   HTTP API: http://localhost:$PORT"
if [ "$NO_UI" = false ]; then
    echo "   Gradio UI: http://localhost:$GRADIO_PORT"
fi
echo "   State dir: $SCRIPT_DIR/.state"
echo "   Docker: $([ $DOCKER_AVAILABLE -eq 1 ] && echo 'Available' || echo 'Not available')"
echo "   (Ports can be changed in Gradio Settings tab)"
echo

# Launch
exec $CMD
