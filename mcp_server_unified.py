#!/usr/bin/env python3
"""
systerd-lite Unified MCP Server

A proper MCP server that supports multiple transports:
- stdio: For VS Code LocalProcess and Claude Desktop
- http: For web clients and Ollama
- sse: Server-Sent Events for streaming responses

Usage:
    # stdio mode (default) - for VS Code / Claude Desktop
    python mcp_server_unified.py
    
    # HTTP mode - for web clients and Ollama
    python mcp_server_unified.py --http --port 8090
    
    # SSE mode - for streaming clients
    python mcp_server_unified.py --sse --port 8090

Configuration for Claude Desktop (~/.config/claude/claude_desktop_config.json):
{
  "mcpServers": {
    "systerd": {
      "command": "python3",
      "args": ["/path/to/mcp_server_unified.py"]
    }
  }
}

Configuration for VS Code (.vscode/mcp.json):
{
  "servers": {
    "systerd": {
      "type": "stdio",
      "command": "python3",
      "args": ["/path/to/mcp_server_unified.py"]
    }
  }
}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Configure logging to stderr (NEVER write to stdout for stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger('mcp-server')

# Add systerd_lite to path and use venv if available
script_dir = Path(__file__).parent.resolve()
venv_site_packages = script_dir / ".venv" / "lib"
if venv_site_packages.exists():
    site_packages = list(venv_site_packages.glob("python*/site-packages"))
    if site_packages:
        sys.path.insert(0, str(site_packages[0]))

sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / "systerd_lite"))

try:
    from systerd_lite.context import SysterdContext
    from systerd_lite.modes import ModeController, SysterdMode
    from systerd_lite.neurobus import NeuroBus
    from systerd_lite.mcp import MCPHandler
    from systerd_lite.permissions import PermissionManager, Permission
except ImportError as e:
    logger.error(f"Failed to import systerd modules: {e}")
    sys.exit(1)


class MCPServerCore:
    """Core MCP server logic shared across transports."""

    def __init__(self):
        self.context: Optional[SysterdContext] = None
        self.mcp: Optional[MCPHandler] = None
        self.initialized = False

    def initialize(self):
        """Initialize the systerd context and MCP handler."""
        state_dir = script_dir / ".state"
        state_dir.mkdir(exist_ok=True)

        neurobus = NeuroBus(state_dir / "neurobus.db")
        mode_controller = ModeController(
            state_file=state_dir / "mode.state",
            acl_file=state_dir / "mode.acl",
        )
        permissions = PermissionManager(state_dir / "permissions.json")

        self.context = SysterdContext(
            state_dir=state_dir,
            socket_path=state_dir / "systerd.sock",
            mode_controller=mode_controller,
            neurobus=neurobus,
            acl_file=state_dir / "mode.acl",
            permission_manager=permissions,
        )

        self.mcp = MCPHandler(self.context)
        self.initialized = True
        logger.info(f"MCP Server initialized with {len(self.mcp.tools)} tools")

    def get_enabled_tools(self) -> List[Dict[str, Any]]:
        """Get list of enabled tools only (respecting permissions)."""
        if not self.mcp:
            return []
        
        perm_mgr = self.context.permission_manager
        enabled_tools = []
        
        for name, tool in self.mcp.tools.items():
            perm = perm_mgr.check(name)
            if perm != Permission.DISABLED:
                enabled_tools.append(tool.to_schema())
        
        return enabled_tools

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools regardless of permission status."""
        if not self.mcp:
            return []
        return [tool.to_schema() for tool in self.mcp.tools.values()]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool and return result."""
        if not self.mcp:
            raise RuntimeError("MCP not initialized")
        
        if name not in self.mcp.tools:
            raise ValueError(f"Tool not found: {name}")
        
        # Reload permissions to get fresh state
        self.context.permission_manager.load()
        
        # Check permission
        perm = self.context.permission_manager.check(name)
        if perm == Permission.DISABLED:
            raise PermissionError(f"Tool '{name}' is disabled")
        
        # Execute tool
        result = await self.mcp.tools[name].handler(**arguments)
        return result

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {},
            },
            "serverInfo": {
                "name": "systerd-lite",
                "version": "3.0.0",
            },
        }

    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request - returns only enabled tools."""
        # Reload permissions to get fresh state
        self.context.permission_manager.load()
        tools = self.get_enabled_tools()
        return {"tools": tools}

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            raise ValueError("Missing tool name")
        
        result = await self.call_tool(name, arguments)
        content = [{"type": "text", "text": json.dumps(result, default=str, ensure_ascii=False)}]
        return {"content": content}

    async def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request and return result."""
        if method == "initialize":
            return self.handle_initialize(params)
        elif method == "tools/list":
            return await self.handle_tools_list(params)
        elif method == "tools/call":
            return await self.handle_tools_call(params)
        elif method == "resources/list":
            return {"resources": []}
        elif method == "prompts/list":
            return {"prompts": []}
        elif method == "ping":
            return {}
        else:
            raise ValueError(f"Method not found: {method}")


class StdioTransport:
    """stdio transport for VS Code LocalProcess and Claude Desktop."""

    def __init__(self, core: MCPServerCore):
        self.core = core
        self.running = False

    async def read_message(self) -> Optional[Dict[str, Any]]:
        """Read a JSON-RPC message from stdin."""
        loop = asyncio.get_event_loop()
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                return None
            line = line.strip()
            if not line:
                return None
            logger.debug(f"Received: {line[:200]}...")
            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Read error: {e}")
            return None

    def write_message(self, message: Dict[str, Any]):
        """Write a JSON-RPC message to stdout."""
        line = json.dumps(message, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        logger.debug(f"Sent: {line[:200]}...")

    def send_error(self, msg_id: Any, code: int, message: str, data: Any = None):
        """Send a JSON-RPC error response."""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        self.write_message({"jsonrpc": "2.0", "id": msg_id, "error": error})

    def send_result(self, msg_id: Any, result: Any):
        """Send a JSON-RPC result response."""
        self.write_message({"jsonrpc": "2.0", "id": msg_id, "result": result})

    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a single JSON-RPC message."""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        # Notifications (no id) - no response expected
        if msg_id is None:
            if method == "notifications/initialized":
                logger.info("Client initialized notification received")
            elif method == "notifications/cancelled":
                logger.info("Received cancellation notification")
            else:
                logger.warning(f"Unknown notification: {method}")
            return

        # Requests (have id) - response required
        try:
            result = await self.core.handle_request(method, params)
            self.send_result(msg_id, result)
        except PermissionError as e:
            self.send_error(msg_id, -32001, str(e))
        except ValueError as e:
            self.send_error(msg_id, -32602, str(e))
        except Exception as e:
            logger.exception(f"Error handling {method}: {e}")
            self.send_error(msg_id, -32603, str(e))

    async def run(self):
        """Main server loop."""
        logger.info("Starting MCP stdio server...")
        self.core.initialize()

        self.running = True
        while self.running:
            message = await self.read_message()
            if message is None:
                logger.info("End of input, shutting down")
                break
            await self.handle_message(message)

        logger.info("MCP stdio server stopped")


class HTTPTransport:
    """HTTP transport for web clients and Ollama."""

    def __init__(self, core: MCPServerCore, port: int = 8090):
        self.core = core
        self.port = port
        self.app = None

    async def run(self):
        """Start HTTP server."""
        try:
            import aiohttp.web
        except ImportError:
            logger.error("aiohttp not installed. Run: pip install aiohttp")
            sys.exit(1)

        logger.info(f"Starting MCP HTTP server on port {self.port}...")
        self.core.initialize()

        app = aiohttp.web.Application()
        app.add_routes([
            aiohttp.web.get('/health', self.handle_health),
            aiohttp.web.get('/tools', self.handle_tools_list),
            aiohttp.web.post('/call', self.handle_call),
            aiohttp.web.post('/mcp', self.handle_mcp),
            aiohttp.web.post('/', self.handle_mcp),
        ])

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()

        logger.info(f"MCP HTTP server running at http://localhost:{self.port}")
        logger.info("Endpoints:")
        logger.info(f"  GET  /health - Health check")
        logger.info(f"  GET  /tools  - List enabled tools")
        logger.info(f"  POST /call   - Call a tool ({{name, arguments}})")
        logger.info(f"  POST /mcp    - JSON-RPC endpoint")

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Shutting down HTTP server...")

    async def handle_health(self, request) -> 'aiohttp.web.Response':
        import aiohttp.web
        return aiohttp.web.json_response({
            "status": "healthy",
            "version": "3.0.0",
            "tools": len(self.core.mcp.tools) if self.core.mcp else 0,
            "enabled_tools": len(self.core.get_enabled_tools()) if self.core.mcp else 0,
            "timestamp": datetime.now().isoformat(),
        })

    async def handle_tools_list(self, request) -> 'aiohttp.web.Response':
        import aiohttp.web
        tools = self.core.get_enabled_tools()
        return aiohttp.web.json_response({
            "tools": tools,
            "count": len(tools),
        })

    async def handle_call(self, request) -> 'aiohttp.web.Response':
        import aiohttp.web
        try:
            data = await request.json()
            name = data.get("name")
            arguments = data.get("arguments", {})
            
            result = await self.core.call_tool(name, arguments)
            return aiohttp.web.json_response({"result": result})
        except PermissionError as e:
            return aiohttp.web.json_response({"error": str(e)}, status=403)
        except ValueError as e:
            return aiohttp.web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            return aiohttp.web.json_response({"error": str(e)}, status=500)

    async def handle_mcp(self, request) -> 'aiohttp.web.Response':
        """Handle JSON-RPC MCP requests."""
        import aiohttp.web
        try:
            data = await request.json()
            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")

            # Handle notification (no response needed but return empty)
            if msg_id is None:
                return aiohttp.web.json_response({})

            result = await self.core.handle_request(method, params)
            return aiohttp.web.json_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            })
        except Exception as e:
            return aiohttp.web.json_response({
                "jsonrpc": "2.0",
                "id": data.get("id") if isinstance(data, dict) else None,
                "error": {"code": -32603, "message": str(e)},
            }, status=200)  # JSON-RPC errors still return 200


class SSETransport:
    """Server-Sent Events transport for streaming responses."""

    def __init__(self, core: MCPServerCore, port: int = 8090):
        self.core = core
        self.port = port
        self.clients: List[asyncio.Queue] = []

    async def run(self):
        """Start SSE server."""
        try:
            import aiohttp.web
        except ImportError:
            logger.error("aiohttp not installed. Run: pip install aiohttp")
            sys.exit(1)

        logger.info(f"Starting MCP SSE server on port {self.port}...")
        self.core.initialize()

        app = aiohttp.web.Application()
        app.add_routes([
            aiohttp.web.get('/health', self.handle_health),
            aiohttp.web.get('/sse', self.handle_sse),
            aiohttp.web.post('/message', self.handle_message),
        ])

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()

        logger.info(f"MCP SSE server running at http://localhost:{self.port}")
        logger.info("Endpoints:")
        logger.info(f"  GET  /health  - Health check")
        logger.info(f"  GET  /sse     - SSE stream endpoint")
        logger.info(f"  POST /message - Send JSON-RPC message")

        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Shutting down SSE server...")

    async def handle_health(self, request) -> 'aiohttp.web.Response':
        import aiohttp.web
        return aiohttp.web.json_response({
            "status": "healthy",
            "version": "3.0.0",
            "transport": "sse",
            "clients": len(self.clients),
        })

    async def handle_sse(self, request) -> 'aiohttp.web.StreamResponse':
        """SSE endpoint for clients to receive messages."""
        import aiohttp.web
        
        response = aiohttp.web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            }
        )
        await response.prepare(request)

        queue = asyncio.Queue()
        self.clients.append(queue)

        # Send initial endpoint info
        endpoint_event = f"event: endpoint\ndata: /message\n\n"
        await response.write(endpoint_event.encode())

        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    event = f"event: message\ndata: {json.dumps(message)}\n\n"
                    await response.write(event.encode())
                except asyncio.TimeoutError:
                    # Send keepalive
                    await response.write(b": keepalive\n\n")
        except asyncio.CancelledError:
            pass
        finally:
            self.clients.remove(queue)

        return response

    async def handle_message(self, request) -> 'aiohttp.web.Response':
        """Receive JSON-RPC message and broadcast response via SSE."""
        import aiohttp.web
        
        try:
            data = await request.json()
            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")

            result = await self.core.handle_request(method, params)
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }

            # Broadcast to all SSE clients
            for queue in self.clients:
                await queue.put(response)

            return aiohttp.web.json_response({"status": "sent"})
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": data.get("id") if isinstance(data, dict) else None,
                "error": {"code": -32603, "message": str(e)},
            }
            for queue in self.clients:
                await queue.put(error_response)
            return aiohttp.web.json_response({"status": "error", "message": str(e)}, status=500)


def main():
    parser = argparse.ArgumentParser(
        description='systerd-lite Unified MCP Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # stdio mode (default) - for VS Code / Claude Desktop
  python mcp_server_unified.py
  
  # HTTP mode - for web clients and Ollama
  python mcp_server_unified.py --http --port 8090
  
  # SSE mode - for streaming
  python mcp_server_unified.py --sse --port 8090
  
  # Debug mode
  python mcp_server_unified.py --debug
"""
    )
    
    parser.add_argument('--http', action='store_true',
                        help='Use HTTP transport instead of stdio')
    parser.add_argument('--sse', action='store_true',
                        help='Use SSE transport instead of stdio')
    parser.add_argument('--port', type=int, default=8090,
                        help='Port for HTTP/SSE server (default: 8090)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    core = MCPServerCore()
    
    if args.sse:
        transport = SSETransport(core, args.port)
    elif args.http:
        transport = HTTPTransport(core, args.port)
    else:
        transport = StdioTransport(core)
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(transport.run())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
