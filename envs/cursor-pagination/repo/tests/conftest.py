from __future__ import annotations

import pytest

from pagewalk import Page


@pytest.fixture
def scripted_fetcher():
    def build(pages: dict[str | None, Page]):
        calls: list[tuple[str | None, int]] = []

        def fetch(cursor: str | None, page_size: int) -> Page:
            calls.append((cursor, page_size))
            return pages[cursor]

        fetch.calls = calls
        return fetch

    return build
