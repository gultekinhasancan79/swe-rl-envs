from pagewalk import Page


def test_page_from_iterable_freezes_items():
    source = ["a", "b"]
    page = Page.from_iterable(source, next_cursor="next")
    source.append("c")

    assert page.items == ("a", "b")
    assert page.next_cursor == "next"


def test_page_accepts_terminal_cursor():
    page = Page(("only",), None)

    assert page.items == ("only",)
    assert page.next_cursor is None
