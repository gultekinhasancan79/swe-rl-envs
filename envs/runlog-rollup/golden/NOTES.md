# Reference solution — OPS-3312

## Root cause

`accumulate_statuses` declared its accumulator as

```python
def accumulate_statuses(records, into: Counter = Counter()) -> Counter:
```

A default argument is evaluated **once**, when the `def` executes at import
time — not on each call. So every call that omits `into` tallies into the same
`Counter` object, and that object lives for the lifetime of the process.

`summarize_file` omits `into`. Processing shard A leaves A's tallies in the
shared counter; processing shard B in the same process then adds B's records on
top of them. The first file in a process is always right, which is why
single-shard runs matched the dashboard and nobody caught it for weeks.

It also explains the specific shape of the symptom in the ticket:
`record_count` comes from `len(records)` and stays correct, while
`status_counts` inflates — hence a shard reporting `total=6` with status
columns summing to 11. `build_rollup` derives OVERALL by summing the per-file
dicts, so the corruption propagates upward.

## Fix

Use `None` as the sentinel and allocate a fresh `Counter` per call:

```python
def accumulate_statuses(records, into: Counter | None = None) -> Counter:
    counts = Counter() if into is None else into
```

This restores the behaviour the docstring already claimed, and preserves the
fold-into-a-caller's-counter contract that the reliability dashboard depends
on. One line of behaviour change; no API, output format or fixture changes.

## Rejected alternatives

- **`into.clear()` on entry.** Makes the visible suite pass and destroys the
  caller's counter — held-out
  `test_supplied_accumulator_is_folded_into_not_replaced` catches it.
- **Passing `Counter()` explicitly from `summarize_file`.** Fixes the reported
  symptom while leaving the shared default in place for every other caller —
  held-out `test_omitted_accumulator_starts_from_empty_every_call` catches it.
- **Copying the counter on return.** Hides the leak for one call and still
  accumulates forever; fails the repeated-call tests.
