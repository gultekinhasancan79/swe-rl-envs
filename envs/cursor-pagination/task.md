# API-4821 — event export silently drops records after filtered pages

The data-export worker uses `pagewalk.collect_all` to consume cursor-paginated
internal APIs. After a backend rollout that moved permission filtering deeper
into the service, some exports started ending early.

What we know from production traces:

- The first request uses a null cursor and the configured page size.
- Some intermediate responses now contain fewer items than the requested page
  size because filtering happens after a shard read.
- Those short responses can still include a non-null `next_cursor`.
- Export jobs using those responses omit everything after the first short page.
- Fully populated pages and normal terminal pages still behave as expected.

## What done looks like

`collect_all` follows the backend cursor contract for any valid sequence of
pages, including short or empty intermediate pages, while preserving existing
public behaviour:

- item order and duplicates are preserved,
- `page_size` is forwarded unchanged,
- `next_cursor is None` is terminal,
- cursor loops are rejected,
- `max_pages` still prevents unbounded traversal,
- and invalid fetcher results still fail loudly.

## Ground rules

- Do not modify anything under `tests/`.
- Keep the public API exported from `pagewalk` intact.
- Do not add dependencies.
- Do not special-case checked-in cursors, values, or test names.
- The environment has no network access.
- Fix the pagination contract, not the fixture.

Leave a short explanation of the root cause with your change.
