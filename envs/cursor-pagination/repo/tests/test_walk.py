import pytest

from pagewalk import Page, PaginationError, collect_all


def test_single_terminal_short_page(scripted_fetcher):
    fetch = scripted_fetcher({None: Page(("a", "b"), None)})

    assert collect_all(fetch, page_size=10) == ["a", "b"]
    assert fetch.calls == [(None, 10)]


def test_exactly_full_terminal_page(scripted_fetcher):
    fetch = scripted_fetcher({None: Page(("a", "b"), None)})

    assert collect_all(fetch, page_size=2) == ["a", "b"]


def test_multiple_full_pages_preserve_order(scripted_fetcher):
    fetch = scripted_fetcher(
        {
            None: Page(("a", "b"), "c1"),
            "c1": Page(("c", "d"), "c2"),
            "c2": Page(("e", "f"), None),
        }
    )

    assert collect_all(fetch, page_size=2) == ["a", "b", "c", "d", "e", "f"]


def test_duplicates_are_preserved(scripted_fetcher):
    fetch = scripted_fetcher(
        {
            None: Page(("a", "a"), "next"),
            "next": Page(("a", "b"), None),
        }
    )

    assert collect_all(fetch, page_size=2) == ["a", "a", "a", "b"]


def test_requested_page_size_is_forwarded(scripted_fetcher):
    fetch = scripted_fetcher(
        {
            None: Page(("a", "b", "c"), "next"),
            "next": Page(("d", "e", "f"), None),
        }
    )

    collect_all(fetch, page_size=3)

    assert fetch.calls == [(None, 3), ("next", 3)]


def test_invalid_page_size_is_rejected():
    with pytest.raises(ValueError, match="page_size"):
        collect_all(lambda cursor, size: Page((), None), page_size=0)


def test_invalid_max_pages_is_rejected():
    with pytest.raises(ValueError, match="max_pages"):
        collect_all(lambda cursor, size: Page((), None), max_pages=0)


def test_fetcher_must_return_page():
    with pytest.raises(TypeError, match="must return Page"):
        collect_all(lambda cursor, size: ["not", "a", "page"], page_size=2)


def test_cursor_loop_is_rejected(scripted_fetcher):
    fetch = scripted_fetcher(
        {
            None: Page(("a",), "loop"),
            "loop": Page(("b",), "loop"),
        }
    )

    with pytest.raises(PaginationError, match="cursor loop"):
        collect_all(fetch, page_size=1)


def test_max_pages_stops_unbounded_cursor_chain():
    counter = 0

    def fetch(cursor, page_size):
        nonlocal counter
        counter += 1
        return Page(("item",), f"cursor-{counter}")

    with pytest.raises(PaginationError, match="max_pages=3"):
        collect_all(fetch, page_size=1, max_pages=3)


def test_short_intermediate_page_still_follows_next_cursor(scripted_fetcher):
    fetch = scripted_fetcher(
        {
            None: Page(("a",), "next"),
            "next": Page(("b", "c"), None),
        }
    )

    assert collect_all(fetch, page_size=2) == ["a", "b", "c"]
    assert fetch.calls == [(None, 2), ("next", 2)]
