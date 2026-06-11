"""Artifact 관련 핸들러.

CommandRouter의 artifact 관련 기능을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.api.ws.commands import CommandRouter


class ArtifactHandler:
    """Artifact 관련 핸들러."""

    def __init__(self, router: "CommandRouter") -> None:
        self._router = router
