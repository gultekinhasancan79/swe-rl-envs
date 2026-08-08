# pagewalk

Small cursor-pagination helper used by internal API clients.

The API services this package talks to are allowed to return fewer than
`page_size` items on an intermediate page. Filtering, permissions, and backend
shard boundaries can all produce a short page. The only authoritative signal
that pagination is finished is `next_cursor is None`.

## Public API

```python
from pagewalk import Page, PaginationError, collect_all
```

`collect_all(fetch_page, page_size=100, max_pages=1000)` calls `fetch_page`
with the current cursor and requested page size until the backend returns a
page whose `next_cursor` is `None`.

The helper preserves item order and duplicates exactly as returned by the
backend. It also rejects cursor loops and enforces a maximum number of pages.

## Tests

```bash
PYTHONPATH=src python -m pytest
```
