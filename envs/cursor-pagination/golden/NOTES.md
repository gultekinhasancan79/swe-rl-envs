# Reference solution — API-4821

## Root cause

`collect_all` treated any page shorter than the requested `page_size` as the
end of pagination:

```python
if len(page.items) < page_size:
    return collected
```

That is valid for offset/page-number APIs only when the server contract says
page fullness is authoritative. This client uses cursor pagination, and the
backend is explicitly allowed to return short or empty intermediate pages while
still returning a non-null `next_cursor`.

The premature return therefore drops every page after the first filtered or
shard-shortened response.

## Fix

Use the cursor contract as the termination condition:

```python
next_cursor = page.next_cursor
if next_cursor is None:
    return collected
```

All existing safety behaviour remains intact: order and duplicates are
preserved, page size is forwarded, cursor loops are rejected, invalid page
objects fail, and `max_pages` still bounds traversal.

## Rejected alternatives

- **Increase `page_size`.** Short intermediate pages are contractually valid at
  any requested size, so this only makes the symptom less frequent.
- **Continue only when the short page is non-empty.** Empty intermediate pages
  with a valid cursor are also allowed.
- **Special-case the visible cursor/value.** Held-out tests generate different
  cursor chains and payloads.
- **Ignore `max_pages` or loop detection.** Fixing termination must not remove
  the existing safeguards against malformed backends.
