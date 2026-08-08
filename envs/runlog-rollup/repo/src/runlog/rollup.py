"""Aggregation of run records into per-file and overall summaries.

The report is deliberately per-file first: when the nightly job fans out over
one shard per runner, the first question in an incident is always "which shard
went bad", not "what is the global pass rate".
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .records import RunRecord, load_records


@dataclass(frozen=True)
class FileSummary:
    """Aggregates for a single record file."""

    path: str
    record_count: int
    status_counts: dict[str, int]
    total_duration_ms: int
    owners: tuple[str, ...]

    @property
    def pass_rate(self) -> float:
        if self.record_count == 0:
            return 0.0
        return self.status_counts.get("passed", 0) / self.record_count


@dataclass(frozen=True)
class Rollup:
    """The whole report: one summary per input file, plus overall totals."""

    files: tuple[FileSummary, ...]
    record_count: int
    status_counts: dict[str, int]
    total_duration_ms: int

    @property
    def pass_rate(self) -> float:
        if self.record_count == 0:
            return 0.0
        return self.status_counts.get("passed", 0) / self.record_count


def accumulate_statuses(
    records: Iterable[RunRecord], into: Counter = Counter()
) -> Counter:
    """Tally ``records`` by status.

    ``into`` lets a caller fold several batches of records into one counter;
    when it is omitted the tally starts from empty.
    """
    counts = into
    for record in records:
        counts[record.status] += 1
    return counts


def summarize_file(path: str | Path, *, strict: bool = True) -> FileSummary:
    """Read one record file and reduce it to a :class:`FileSummary`."""
    records = load_records(path, strict=strict)
    counts = accumulate_statuses(records)
    return FileSummary(
        path=str(path),
        record_count=len(records),
        status_counts=_ordered(counts),
        total_duration_ms=sum(r.duration_ms for r in records),
        owners=tuple(sorted({r.owner for r in records})),
    )


def build_rollup(paths: Sequence[str | Path], *, strict: bool = True) -> Rollup:
    """Summarize every path in ``paths`` and combine them into one report."""
    summaries = tuple(summarize_file(p, strict=strict) for p in paths)

    overall: Counter = Counter()
    for summary in summaries:
        overall.update(summary.status_counts)

    return Rollup(
        files=summaries,
        record_count=sum(s.record_count for s in summaries),
        status_counts=_ordered(overall),
        total_duration_ms=sum(s.total_duration_ms for s in summaries),
    )


def _ordered(counts: Counter) -> dict[str, int]:
    """Counters iterate in insertion order; the report needs a stable one."""
    return {status: counts[status] for status in sorted(counts)}
