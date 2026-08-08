"""Held-out acceptance tests for OPS-3312.

This file is never present in the repository the candidate works in. It is
bind-mounted at verification time only.

Two deliberate properties:

1. Every record file used here is generated at runtime, with different
   pipelines, owners, durations and status mixes than the checked-in fixtures.
   A solution that special-cases the visible fixture paths or hardcodes their
   numbers fails here.

2. The tests pin the *documented contract* of ``accumulate_statuses`` in both
   directions -- a fresh tally when ``into`` is omitted, and folding into the
   caller's counter when it is supplied. A "fix" that clears the shared default
   on entry satisfies the visible suite but breaks the second half, and a "fix"
   that only passes an explicit counter at the call site leaves the default
   still shared and breaks the first half.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

import runlog
from runlog.records import RunRecord
from runlog.report import format_json
from runlog.rollup import accumulate_statuses, build_rollup, summarize_file

SRC = Path(runlog.__file__).resolve().parents[1]


def write_shard(path: Path, statuses: dict[str, int], *, owner: str) -> Path:
    """Write a record file containing exactly ``statuses`` many of each status."""
    lines = []
    run_id = 0
    for status, count in statuses.items():
        for _ in range(count):
            run_id += 1
            lines.append(
                json.dumps(
                    {
                        "run_id": f"{path.stem}-{run_id:04d}",
                        "pipeline": f"pipeline-{path.stem}",
                        "status": status,
                        "duration_ms": 1000 + run_id,
                        "owner": owner,
                    }
                )
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def record(status: str) -> RunRecord:
    return RunRecord(
        run_id="held-1",
        pipeline="held",
        status=status,
        duration_ms=7,
        owner="held-team",
    )


@pytest.fixture
def shards(tmp_path: Path) -> list[Path]:
    """Three shards with deliberately overlapping status keys."""
    return [
        write_shard(
            tmp_path / "alpha.jsonl",
            {"passed": 4, "failed": 2, "timeout": 1},
            owner="team-alpha",
        ),
        write_shard(
            tmp_path / "bravo.jsonl",
            {"passed": 2, "skipped": 3},
            owner="team-bravo",
        ),
        write_shard(
            tmp_path / "charlie.jsonl",
            {"failed": 5, "passed": 1},
            owner="team-charlie",
        ),
    ]


EXPECTED = [
    {"failed": 2, "passed": 4, "timeout": 1},
    {"passed": 2, "skipped": 3},
    {"failed": 5, "passed": 1},
]


# --------------------------------------------------------------------------
# The reported defect
# --------------------------------------------------------------------------


def test_every_shard_is_counted_independently(shards):
    rollup = build_rollup(shards)

    assert [s.status_counts for s in rollup.files] == EXPECTED


def test_status_counts_sum_to_record_count(shards):
    for summary in build_rollup(shards).files:
        assert sum(summary.status_counts.values()) == summary.record_count


def test_overall_is_the_sum_of_the_shards(shards):
    rollup = build_rollup(shards)

    assert rollup.status_counts == {"failed": 7, "passed": 7, "skipped": 3, "timeout": 1}
    assert rollup.record_count == 18


def test_repeated_rollups_in_one_process_are_identical(shards):
    first = build_rollup(shards)
    second = build_rollup(shards)
    third = build_rollup(list(reversed(shards)))

    assert [s.status_counts for s in second.files] == [
        s.status_counts for s in first.files
    ]
    assert [s.status_counts for s in third.files] == list(reversed(EXPECTED))


def test_summarize_file_called_repeatedly_is_stable(shards):
    counts = [summarize_file(shards[0]).status_counts for _ in range(5)]

    assert counts == [EXPECTED[0]] * 5


def test_returned_counts_are_not_shared_state(shards):
    summary = summarize_file(shards[0])
    summary.status_counts["passed"] = 9999

    assert summarize_file(shards[0]).status_counts == EXPECTED[0]


# --------------------------------------------------------------------------
# The documented contract of accumulate_statuses, both directions
# --------------------------------------------------------------------------


def test_omitted_accumulator_starts_from_empty_every_call():
    first = accumulate_statuses([record("passed"), record("failed")])
    second = accumulate_statuses([record("passed")])

    assert dict(first) == {"passed": 1, "failed": 1}
    assert dict(second) == {"passed": 1}
    assert first is not second


def test_supplied_accumulator_is_folded_into_not_replaced():
    running = Counter({"passed": 10, "skipped": 4})

    result = accumulate_statuses([record("passed"), record("timeout")], running)

    assert result is running
    assert dict(running) == {"passed": 11, "skipped": 4, "timeout": 1}


def test_supplied_accumulator_works_as_a_keyword_too():
    running = Counter()

    accumulate_statuses([record("failed")], into=running)

    assert dict(running) == {"failed": 1}


def test_public_api_is_still_exported():
    for name in (
        "accumulate_statuses",
        "build_rollup",
        "summarize_file",
        "FileSummary",
        "Rollup",
    ):
        assert hasattr(runlog, name), f"runlog.{name} disappeared"


# --------------------------------------------------------------------------
# End to end, one process, many shards
# --------------------------------------------------------------------------


def test_cli_reports_each_shard_correctly_in_one_invocation(shards):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    result = subprocess.run(
        [sys.executable, "-m", "runlog", "--format", "json", *map(str, shards)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert [f["status_counts"] for f in payload["files"]] == EXPECTED
    assert payload["overall"]["record_count"] == 18


def test_text_and_json_agree(shards):
    rollup = build_rollup(shards)
    payload = json.loads(format_json(rollup))

    for summary, rendered in zip(rollup.files, payload["files"]):
        assert rendered["status_counts"] == summary.status_counts
        assert rendered["record_count"] == summary.record_count
