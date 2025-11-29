#!/usr/bin/env python3
"""
systerd-lite MCP Server (stdio transport)

This is a proper MCP server that communicates via stdin/stdout using JSON-RPC 2.0.
It is designed to be launched by VS Code's LocalProcess MCP client.

Usage:
    python mcp_server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Configure logging to stderr (NEVER write to stdout for stdio transport)
logging.basicConfig(
    level=logging.DEBUG,
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
    from systerd_lite.permissions import PermissionManager
except ImportError as e:
    logger.error(f"Failed to import systerd modules: {e}")
    sys.exit(1)


class MCPStdioServer:
    """MCP Server using stdio transport (JSON-RPC over stdin/stdout)."""

    def __init__(self):
        self.running = False
        self.context: SysterdContext | None = None
        self.mcp: MCPHandler | None = None

    async def initialize(self):
        """Initialize the systerd context and MCP handler."""
        state_dir = Path(__file__).parent.resolve() / ".state"
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
        logger.info(f"MCP Server initialized with {len(self.mcp.tools)} tools")

    async def read_message(self) -> Dict[str, Any] | None:
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

    async def handle_initialize(self, msg_id: Any, params: Dict[str, Any]) -> None:
        """Handle initialize request."""
        logger.info("Handling initialize request")
        self.send_result(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "systerd-lite",
                "version": "3.0.0",
            },
        })

    async def handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle initialized notification (no response needed)."""
        logger.info("Client initialized notification received")

    async def handle_tools_list(self, msg_id: Any, params: Dict[str, Any]) -> None:
        """Handle tools/list request."""
        logger.info("Handling tools/list request")
        tools = [tool.to_schema() for tool in self.mcp.tools.values()]
        self.send_result(msg_id, {"tools": tools})

    async def handle_tools_call(self, msg_id: Any, params: Dict[str, Any]) -> None:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})
        logger.info(f"Handling tools/call: {name}")

        if not name:
            self.send_error(msg_id, -32602, "Missing tool name")
            return

        if name not in self.mcp.tools:
            self.send_error(msg_id, -32601, f"Tool not found: {name}")
            return

        try:
            result = await self.mcp.tools[name].handler(**arguments)
            content = [{"type": "text", "text": json.dumps(result, default=str, ensure_ascii=False)}]
            self.send_result(msg_id, {"content": content})
        except Exception as e:
            logger.exception(f"Tool execution error: {e}")
            self.send_error(msg_id, -32603, str(e))

    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a single JSON-RPC message."""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        logger.debug(f"Processing method: {method}, id: {msg_id}")

        # Notifications (no id) - no response expected
        if msg_id is None:
            if method == "notifications/initialized":
                await self.handle_initialized(params)
            elif method == "notifications/cancelled":
                logger.info("Received cancellation notification")
            else:
                logger.warning(f"Unknown notification: {method}")
            return

        # Requests (have id) - response required
        if method == "initialize":
            await self.handle_initialize(msg_id, params)
        elif method == "tools/list":
            await self.handle_tools_list(msg_id, params)
        elif method == "tools/call":
            await self.handle_tools_call(msg_id, params)
        elif method == "ping":
            self.send_result(msg_id, {})
        elif method == "resources/list":
            self.send_result(msg_id, {"resources": []})
        elif method == "prompts/list":
            self.send_result(msg_id, {"prompts": []})
        else:
            logger.warning(f"Unsupported method: {method}")
            self.send_error(msg_id, -32601, f"Method not found: {method}")

    async def run(self):
        """Main server loop."""
        logger.info("Starting MCP stdio server...")
        await self.initialize()

        self.running = True
        while self.running:
            message = await self.read_message()
            if message is None:
                logger.info("End of input, shutting down")
                break
            await self.handle_message(message)

        logger.info("MCP server stopped")


def main():
    """Entry point."""
    server = MCPStdioServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
