#!/usr/bin/env python3
"""Entry point for the systerd layer-2 daemon."""

from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path
from typing import Any

from .app import SysterdApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run systerd layer-2 daemon")
    parser.add_argument("--state-dir", type=Path, default=None, help="override state directory")
    parser.add_argument("--socket", type=Path, default=None, help="override UNIX socket path")
    parser.add_argument("--http-port", type=int, default=None, help="enable HTTP server on port")
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    app = SysterdApp(state_dir=args.state_dir, socket_path=args.socket, http_port=args.http_port)
    await app.start()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(signum: int, _frame: Any | None) -> None:
        print(f"[systerd] received signal {signum}, shutting down")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig, None)
        except NotImplementedError:
            pass

    await stop_event.wait()
    await app.stop()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
