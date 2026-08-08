from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Page:
    """One page returned by a cursor-based backend."""

    items: tuple[str, ...]
    next_cursor: str | None

    @classmethod
    def from_iterable(
        cls, items: Iterable[str], *, next_cursor: str | None
    ) -> "Page":
        return cls(tuple(items), next_cursor)
