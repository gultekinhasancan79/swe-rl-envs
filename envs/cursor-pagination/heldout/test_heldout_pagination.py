"""Held-out acceptance tests for the cursor-pagination environment.

The visible suite contains one short-intermediate-page regression. These tests
exercise the broader cursor contract with different cursors, page sizes, empty
intermediate pages, generated payloads, and safety limits.
"""

from __future__ import annotations

from itertools import count

import pytest

from pagewalk import Page, PaginationError, collect_all


def make_fetcher(pages):
    calls = []

    def fetch(cursor, page_size):
        calls.append((cursor, page_size))
        return pages[cursor]

    fetch.calls = calls
    return fetch


def test_empty_intermediate_page_can_still_have_more_data():
    fetch = make_fetcher(
        {
            None: Page((), "after-filter"),
            "after-filter": Page(("visible",), None),
        }
    )

    assert collect_all(fetch, page_size=50) == ["visible"]
    assert fetch.calls == [(None, 50), ("after-filter", 50)]


def test_short_page_between_two_full_pages_does_not_terminate_walk():
    fetch = make_fetcher(
        {
            None: Page(("a", "b", "c"), "one"),
            "one": Page(("d",), "two"),
            "two": Page(("e", "f", "g"), None),
        }
    )

    assert collect_all(fetch, page_size=3) == ["a", "b", "c", "d", "e", "f", "g"]


def test_multiple_consecutive_short_pages_are_followed():
    fetch = make_fetcher(
        {
            None: Page(("a",), "one"),
            "one": Page(("b",), "two"),
            "two": Page(("c",), None),
        }
    )

    assert collect_all(fetch, page_size=4) == ["a", "b", "c"]


def test_short_page_preserves_duplicate_items_across_cursor_boundary():
    fetch = make_fetcher(
        {
            None: Page(("same",), "next"),
            "next": Page(("same", "last"), None),
        }
    )

    assert collect_all(fetch, page_size=5) == ["same", "same", "last"]


def test_empty_string_is_a_valid_non_terminal_cursor():
    fetch = make_fetcher(
        {
            None: Page(("first",), ""),
            "": Page(("second",), None),
        }
    )

    assert collect_all(fetch, page_size=2) == ["first", "second"]


def test_short_page_does_not_hide_cursor_loop():
    fetch = make_fetcher(
        {
            None: Page(("first",), "loop"),
            "loop": Page((), "loop"),
        }
    )

    with pytest.raises(PaginationError, match="cursor loop"):
        collect_all(fetch, page_size=10)


def test_short_pages_still_respect_max_pages():
    sequence = count(1)

    def fetch(cursor, page_size):
        return Page((f"item-{next(sequence)}",), f"cursor-{next(sequence)}")

    with pytest.raises(PaginationError, match="max_pages=2"):
        collect_all(fetch, page_size=10, max_pages=2)


def test_generated_short_pages_collect_all_runtime_values():
    values = [f"event-{n:03d}" for n in range(17)]
    pages = {
        None: Page(tuple(values[:4]), "cursor-a"),
        "cursor-a": Page(tuple(values[4:7]), "cursor-b"),
        "cursor-b": Page(tuple(values[7:15]), "cursor-c"),
        "cursor-c": Page(tuple(values[15:]), None),
    }
    fetch = make_fetcher(pages)

    assert collect_all(fetch, page_size=8) == values


def test_terminal_empty_page_finishes_normally():
    fetch = make_fetcher(
        {
            None: Page(("a", "b"), "done"),
            "done": Page((), None),
        }
    )

    assert collect_all(fetch, page_size=2) == ["a", "b"]


def test_full_pages_with_terminal_cursor_remain_supported():
    fetch = make_fetcher(
        {
            None: Page(("a", "b"), "next"),
            "next": Page(("c", "d"), None),
        }
    )

    assert collect_all(fetch, page_size=2) == ["a", "b", "c", "d"]
