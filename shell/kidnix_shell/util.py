"""Small shared helpers."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def paginate(items: list[T], per_page: int) -> list[list[T]]:
    """Split into fixed-size pages.

    SYNTHESIS A4: there is no free scrolling anywhere in the shell. Every list
    a child sees is paginated with big arrows and page dots, so every list
    goes through here. An empty list is one empty page -- the UI still needs
    something to show.
    """
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    if not items:
        return [[]]
    return [items[i : i + per_page] for i in range(0, len(items), per_page)]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
