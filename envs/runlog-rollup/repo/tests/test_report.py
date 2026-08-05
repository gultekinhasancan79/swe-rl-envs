"""Rendering tests.

These build ``Rollup`` values by hand rather than reading files: the formatters
are pure, and keeping them decoupled from disk means a formatting change never
needs a fixture change.
"""

from __future__ import annotations

import json

from runlog.report import format_json, format_text
from runlog.rollup import FileSummary, Rollup

SUMMARY = FileSummary(
    path="shard_a.jsonl",
    record_count=5,
    status_counts={"failed": 1, "passed": 3, "skipped": 1},
    total_duration_ms=331775,
    owners=("billing", "data-platform", "search"),
)

ROLLUP = Rollup(
    files=(SUMMARY,),
    record_count=5,
    status_counts={"failed": 1, "passed": 3, "skipped": 1},
    total_duration_ms=331775,
)


def test_text_report_shows_every_status_column():
    text = format_text(ROLLUP)

    assert "shard_a.jsonl" in text
    assert "total=5 passed=3 failed=1 skipped=1 timeout=0" in text
    assert "OVERALL" in text


def test_text_report_shows_pass_rate_and_owners():
    text = format_text(ROLLUP)

    assert "pass rate 60.0%" in text
    assert "owners billing, data-platform, search" in text


def test_json_report_is_stable_and_sorted():
    payload = json.loads(format_json(ROLLUP))

    assert payload["files"][0]["path"] == "shard_a.jsonl"
    assert payload["files"][0]["status_counts"] == {
        "failed": 1,
        "passed": 3,
        "skipped": 1,
    }
    assert payload["overall"]["record_count"] == 5
    assert payload["overall"]["total_duration_ms"] == 331775


def test_empty_rollup_renders_without_dividing_by_zero():
    empty = Rollup(files=(), record_count=0, status_counts={}, total_duration_ms=0)

    text = format_text(empty)

    assert "pass rate 0.0%" in text
    assert "files 0" in text
