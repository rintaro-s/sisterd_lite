from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from .context import SysterdContext

logger = logging.getLogger(__name__)
from .ai.handler import AIHandler
from .device.bridge import DeviceBridge
from .dbus.proxy import DBusProxy
from .ipc.router import CommandRouter
from .permissions import PermissionManager
from .ipc.server import UnixCommandServer
from .modes import ModeController
from .neurobus import NeuroBus
from .systemd import SystemdBridge


def _default_state_dir() -> Path:
    """Fallback to /var/lib/systerd (production) or .state (dev) depending on permissions."""
    if os.geteuid() == 0:
        return Path("/var/lib/systerd")
    return Path.cwd() / ".state"


STATE_DIR = Path(os.environ.get("SYSTERD_STATE_DIR", _default_state_dir()))
SOCKET_PATH = Path(os.environ.get("SYSTERD_SOCKET", "/run/systerd.sock" if os.geteuid() == 0 else "/tmp/systerd.sock"))


class SysterdApp:
    """Assembles subsystems (mode control, neuro bus, IPC, optional HTTP) and exposes async lifecycle."""

    def __init__(
        self,
        *,
        state_dir: Path | None = None,
        socket_path: Path | None = None,
        http_port: int | None = None,
    ) -> None:
        self.state_dir = state_dir or STATE_DIR
        self.state_dir.mkdir(exist_ok=True, parents=True)
        self.socket_path = socket_path or SOCKET_PATH
        self.http_port = http_port
        mode_file = self.state_dir / "mode.json"
        acl_file = self.state_dir / "mode.acl"
        neuro_file = self.state_dir / "neurobus.sqlite"
        mode_controller = ModeController(state_file=mode_file, acl_file=acl_file)
        neurobus = NeuroBus(storage=neuro_file, max_rows=100_000)
        systemd_bridge = SystemdBridge()
        self.context = SysterdContext(
            state_dir=self.state_dir,
            socket_path=self.socket_path,
            mode_controller=mode_controller,
            neurobus=neurobus,
            acl_file=acl_file,
            systemd_bridge=systemd_bridge,
            dbus_proxy=None,
            ai_handler=None,
            device_bridge=None,
        )
        ai_handler = AIHandler(self.context)
        self.context.ai_handler = ai_handler
        
        device_bridge = DeviceBridge(self.context)
        self.context.device_bridge = device_bridge
        
        permission_file = self.state_dir / "permissions.json"
        permission_manager = PermissionManager(permission_file)
        self.context.permission_manager = permission_manager
        
        # Hook AI handler to systemd events
        def _job_callback(payload):
            if payload.get("result") != "done":
                asyncio.create_task(
                    ai_handler.on_service_failure(
                        payload.get("unit", "unknown"),
                        payload.get("result", "unknown"),
                        payload.get("job_id", -1)
                    )
                )
        
        systemd_bridge.on_job_removed(_job_callback)

        try:
            dbus_proxy = DBusProxy(self.context, systemd_bridge)
            self.context.dbus_proxy = dbus_proxy
        except Exception as e:
            logger.warning(f"D-Bus proxy initialization failed (skipping D-Bus integration): {e}")
            self.context.dbus_proxy = None
        self.router = CommandRouter(self.context)
        self.server = UnixCommandServer(self.socket_path, self.router)
        self.http_server = None
        if self.http_port:
            from .http.server import HTTPServer

            self.http_server = HTTPServer(self.context, port=self.http_port)

    async def start(self) -> None:
        await self.server.start()
        if self.context.dbus_proxy:
            try:
                await self.context.dbus_proxy.start()
            except Exception as e:
                logger.warning(f"D-Bus proxy start failed (continuing without D-Bus): {e}")
        if self.http_server:
            await self.http_server.start()

    async def stop(self) -> None:
        await self.server.close()
        if self.context.dbus_proxy:
            await self.context.dbus_proxy.stop()
        if self.http_server:
            await self.http_server.stop()


def main():
    """Entry point for systerd command."""
    import argparse
    import logging
    import signal
    
    parser = argparse.ArgumentParser(description="Systerd - AI-Native System Manager")
    parser.add_argument("--mode", default="pid2", help="Operating mode (pid1/pid2)")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP server port")
    parser.add_argument("--gradio-port", type=int, default=7860, help="Gradio UI port")
    parser.add_argument("--state-dir", type=Path, help="State directory")
    parser.add_argument("--socket-path", type=Path, help="UNIX socket path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting systerd v3.0 (Deep Fusion)")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"HTTP port: {args.http_port}")
    logger.info(f"Gradio port: {args.gradio_port}")
    
    app = SysterdApp(
        state_dir=args.state_dir,
        socket_path=args.socket_path,
        http_port=args.http_port,
    )
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        loop.create_task(app.stop())
        loop.stop()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        loop.run_until_complete(app.start())
        logger.info("systerd started successfully")
        
        # Start Gradio UI in background if requested
        if args.gradio_port:
            try:
                from .ui.app import launch_gradio_ui
                import threading
                ui_thread = threading.Thread(
                    target=lambda: launch_gradio_ui(app.context, port=args.gradio_port),
                    daemon=True
                )
                ui_thread.start()
                logger.info(f"Gradio UI started on port {args.gradio_port}")
            except Exception as e:
                logger.warning(f"Failed to start Gradio UI: {e}")
        
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        loop.run_until_complete(app.stop())
        loop.close()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
