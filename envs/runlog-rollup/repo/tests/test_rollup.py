"""Aggregation tests.

Historically this layer was covered indirectly through the CLI smoke tests in
``test_cli.py``; the direct multi-shard case below was added when the nightly
report started disagreeing with the runner dashboards (OPS-3312).
"""

from __future__ import annotations

from collections import Counter

from runlog.records import RunRecord
from runlog.rollup import FileSummary, accumulate_statuses, build_rollup


def _record(status: str) -> RunRecord:
    return RunRecord(
        run_id="r-1",
        pipeline="nightly-etl",
        status=status,
        duration_ms=1,
        owner="data-platform",
    )


def test_accumulate_statuses_folds_into_a_caller_supplied_counter():
    running = Counter({"passed": 2})

    result = accumulate_statuses([_record("passed"), _record("failed")], running)

    assert result is running
    assert dict(running) == {"passed": 3, "failed": 1}


def test_pass_rate_is_zero_when_there_are_no_records():
    summary = FileSummary(
        path="empty.jsonl",
        record_count=0,
        status_counts={},
        total_duration_ms=0,
        owners=(),
    )

    assert summary.pass_rate == 0.0


def test_rollup_of_no_files_is_empty():
    rollup = build_rollup([])

    assert rollup.files == ()
    assert rollup.record_count == 0
    assert rollup.status_counts == {}


def test_rollup_over_two_shards_keeps_per_file_counts_separate(shard_a, shard_b):
    rollup = build_rollup([shard_a, shard_b])

    first, second = rollup.files

    assert first.record_count == 5
    assert first.status_counts == {"failed": 1, "passed": 3, "skipped": 1}

    assert second.record_count == 6
    assert second.status_counts == {"failed": 2, "passed": 3, "timeout": 1}
