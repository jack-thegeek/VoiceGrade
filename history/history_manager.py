"""修改历史 / Undo（对应 TODO 第 16 节）。"""
from __future__ import annotations

from typing import Optional

from models.command import HistoryItem


class HistoryManager:
    """内存中的修改历史，支持撤销上一次修改。"""

    def __init__(self, max_size: int = 500) -> None:
        self._items: list[HistoryItem] = []
        self._max_size = max_size

    def push(self, item: HistoryItem) -> None:
        self._items.append(item)
        if len(self._items) > self._max_size:
            self._items.pop(0)

    def undo_last(self) -> Optional[HistoryItem]:
        """弹出并返回最后一次修改记录（用于撤销），无记录返回 None。"""
        if not self._items:
            return None
        return self._items.pop()

    def last(self) -> Optional[HistoryItem]:
        return self._items[-1] if self._items else None

    def clear(self) -> None:
        self._items.clear()

    def all(self) -> list[HistoryItem]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)


__all__ = ["HistoryManager"]