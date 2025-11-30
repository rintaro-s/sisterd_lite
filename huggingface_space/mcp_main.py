#!/usr/bin/env python3
"""
systerd-lite MCP Server for Hugging Face Space

This is a stdio-based MCP server that uses the FULL systerd_lite module.
It reads JSON-RPC requests from stdin and writes responses to stdout.

Usage:
    python mcp_main.py

The server implements the MCP (Model Context Protocol) specification
with ALL 199+ tools from systerd_lite - NO COMPROMISES.
"""

import json
import sys
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

# Configure logging to stderr (stdout is for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("mcp_server")

# Add systerd_lite to path
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

# Import systerd_lite modules
from systerd_lite.context import SysterdContext
from systerd_lite.modes import ModeController, SysterdMode
from systerd_lite.neurobus import NeuroBus
from systerd_lite.permissions import PermissionManager, Permission
from systerd_lite.mcp import MCPHandler


def create_context() -> SysterdContext:
    """Create a SysterdContext for the MCP handler."""
    state_dir = script_dir / ".state"
    state_dir.mkdir(exist_ok=True)
    
    socket_path = state_dir / "systerd.sock"
    acl_file = state_dir / "mode.acl"
    
    # Initialize mode controller
    mode_controller = ModeController(
        state_file=state_dir / "mode.json",
        acl_file=acl_file
    )
    
    # Initialize NeuroBus
    neurobus = NeuroBus(
        storage=state_dir / "neurobus.db",
        max_rows=10000,
        retention_days=7
    )
    
    # Create context
    context = SysterdContext(
        state_dir=state_dir,
        socket_path=socket_path,
        mode_controller=mode_controller,
        neurobus=neurobus,
        acl_file=acl_file
    )
    
    # Initialize permission manager
    perm_file = state_dir / "permissions.json"
    context.permission_manager = PermissionManager(perm_file)
    
    return context


async def main():
    """Main entry point for stdio MCP server with FULL systerd_lite."""
    # Create context and handler with ALL tools
    context = create_context()
    handler = MCPHandler(context)
    
    logger.info(f"MCP Server started with {len(handler.tools)} tools (FULL systerd_lite - NO COMPROMISE)")
    
    # Setup stdin/stdout streams
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    
    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())
    
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            
            try:
                request = json.loads(line.decode('utf-8'))
                response = await handler.process_request(request)
                response_str = json.dumps(response) + '\n'
                writer.write(response_str.encode('utf-8'))
                await writer.drain()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"}
                }
                writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
                await writer.drain()
            except Exception as e:
                logger.exception("Error processing request")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }
                writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
                await writer.drain()
    
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    finally:
        writer.close()
        context.neurobus.close()
        logger.info("MCP Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
