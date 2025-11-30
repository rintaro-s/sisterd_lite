from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .modes import ModeController
from .neurobus import NeuroBus


@dataclass
class SysterdContext:
    """Holds shared components for systerd subsystems."""

    state_dir: Path
    socket_path: Path
    mode_controller: ModeController
    neurobus: NeuroBus
    acl_file: Path
    dbus_proxy: object | None = None
    systemd_bridge: object | None = None
    ai_handler: object | None = None
    device_bridge: object | None = None
    permission_manager: object | None = None
