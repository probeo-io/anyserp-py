from __future__ import annotations

from typing import Any


class AnySerpError(Exception):
    """Base error for all AnySerp operations."""

    def __init__(
        self,
        code: int,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.metadata: dict[str, Any] = metadata or {}
