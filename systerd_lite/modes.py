"""Mode control for systerd.

Provides three operational layers:
- Transparent: forward everything to systemd
- Hybrid: intercept + optimize selected requests
- Dominant: systerd replaces systemd functionality
"""

from __future__ import annotations

import enum
import json
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Set


class SysterdMode(str, enum.Enum):
    TRANSPARENT = "transparent"
    HYBRID = "hybrid"
    DOMINANT = "dominant"


@dataclass
class ModePolicy:
    name: str
    description: str
    intercept_dbus: bool
    allow_systemd_jobs: bool
    ai_decision_required: bool


DEFAULT_POLICIES: Dict[SysterdMode, ModePolicy] = {
    SysterdMode.TRANSPARENT: ModePolicy(
        name="transparent",
        description="systemd handles most operations; systerd observes",
        intercept_dbus=False,
        allow_systemd_jobs=True,
        ai_decision_required=False,
    ),
    SysterdMode.HYBRID: ModePolicy(
        name="hybrid",
        description="systerd intercepts requests and may defer to systemd",
        intercept_dbus=True,
        allow_systemd_jobs=True,
        ai_decision_required=True,
    ),
    SysterdMode.DOMINANT: ModePolicy(
        name="dominant",
        description="systerd executes jobs directly and keeps systemd halted",
        intercept_dbus=True,
        allow_systemd_jobs=False,
        ai_decision_required=True,
    ),
}


class ModeController:
    """Tracks current mode, ACLs and persists state on disk."""

    def __init__(
        self,
        state_file: Path,
        *,
        acl_file: Optional[Path] = None,
        on_change: Optional[Callable[[ModePolicy], None]] = None,
    ) -> None:
        self.state_file = state_file
        self.acl_file = acl_file or state_file.with_name("mode.acl")
        self.on_change = on_change
        self._mode: SysterdMode = SysterdMode.TRANSPARENT
        self.allowed_tokens: Set[str] = set()
        self.load()
        self._load_acl()

    @property
    def mode(self) -> SysterdMode:
        return self._mode

    @property
    def policy(self) -> ModePolicy:
        return DEFAULT_POLICIES[self._mode]

    def set_mode(self, mode: SysterdMode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self.state_file.write_text(json.dumps({"mode": mode.value}))
        if self.on_change:
            self.on_change(self.policy)

    def load(self) -> None:
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            mode_str = data.get("mode", SysterdMode.TRANSPARENT.value)
            try:
                self._mode = SysterdMode(mode_str)
            except ValueError:
                self._mode = SysterdMode.TRANSPARENT
        else:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps({"mode": self._mode.value}))

    def authorize(self, token: Optional[str]) -> None:
        if not self.allowed_tokens:
            return
        if not token:
            raise PermissionError("mode change requires token")
        if token not in self.allowed_tokens:
            raise PermissionError("invalid mode token")

    def summary(self) -> str:
        policy = self.policy
        return (
            f"mode={policy.name} intercept_dbus={policy.intercept_dbus} "
            f"allow_systemd_jobs={policy.allow_systemd_jobs} ai_required={policy.ai_decision_required}"
        )

    def _load_acl(self) -> None:
        if self.acl_file.exists():
            data = json.loads(self.acl_file.read_text())
            tokens = data.get("tokens", [])
            self.allowed_tokens = set(tokens)
            return
        token = os.environ.get("SYSTERD_MODE_TOKEN") or secrets.token_hex(16)
        self.acl_file.parent.mkdir(parents=True, exist_ok=True)
        self.acl_file.write_text(json.dumps({"tokens": [token]}, indent=2))
        self.allowed_tokens = {token}
        print(f"[systerd] generated mode token stored at {self.acl_file}")
