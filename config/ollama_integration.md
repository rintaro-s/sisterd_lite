# Ollama MCP Integration
# 
# systerd-lite provides an HTTP endpoint for Ollama integration.
#
# Start the HTTP server:
#   python3 mcp_server_unified.py --http --port 8090
#
# Then configure Ollama to use the MCP endpoint:
#   - Base URL: http://localhost:8090
#   - Tools endpoint: GET /tools
#   - Call endpoint: POST /call
#
# Example API calls:
#
# 1. List available tools:
#    curl http://localhost:8090/tools
#
# 2. Call a tool:
#    curl -X POST http://localhost:8090/call \
#      -H "Content-Type: application/json" \
#      -d '{"name": "get_uptime", "arguments": {}}'
#
# 3. JSON-RPC endpoint (for MCP-compatible clients):
#    curl -X POST http://localhost:8090/mcp \
#      -H "Content-Type: application/json" \
#      -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
#
# For Ollama with tool calling, you can use the HTTP endpoint to:
# 1. Get tool definitions via GET /tools
# 2. Execute tools via POST /call
#
# The server respects permission settings from the Gradio UI or MCP config tools.
