from __future__ import annotations

from collections.abc import Callable

from .models import Page


class PaginationError(RuntimeError):
    """The backend returned a pagination sequence that cannot be completed."""


FetchPage = Callable[[str | None, int], Page]


def collect_all(
    fetch_page: FetchPage,
    *,
    page_size: int = 100,
    max_pages: int = 1000,
) -> list[str]:
    """Collect every item from a cursor-paginated backend.

    The backend cursor is authoritative. A page may be shorter than
    ``page_size`` and still have a ``next_cursor``.
    """
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")

    cursor: str | None = None
    seen_cursors: set[str] = set()
    collected: list[str] = []

    for _ in range(max_pages):
        page = fetch_page(cursor, page_size)
        if not isinstance(page, Page):
            raise TypeError("fetch_page must return Page")

        collected.extend(page.items)

        # BUG: a short page is not necessarily terminal. Filtering and shard
        # boundaries can produce fewer than page_size items while next_cursor
        # still points to more data.
        if len(page.items) < page_size:
            return collected

        next_cursor = page.next_cursor
        if next_cursor is None:
            return collected

        if next_cursor in seen_cursors:
            raise PaginationError(f"cursor loop detected at {next_cursor!r}")

        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise PaginationError(f"pagination exceeded max_pages={max_pages}")
