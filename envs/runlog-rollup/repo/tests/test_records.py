"""Parsing-level tests. These never touch the aggregation layer."""

from __future__ import annotations

import pytest

from runlog.records import RecordError, RunRecord, load_records


def test_load_records_parses_every_field(shard_a):
    records = load_records(shard_a)

    assert len(records) == 5
    assert records[0] == RunRecord(
        run_id="r-20418",
        pipeline="nightly-etl",
        status="passed",
        duration_ms=84120,
        owner="data-platform",
    )


def test_blank_lines_are_ignored(fixtures):
    assert load_records(fixtures / "empty.jsonl") == []


def test_truncated_json_reports_path_and_line(fixtures):
    with pytest.raises(RecordError) as excinfo:
        load_records(fixtures / "malformed.jsonl")

    assert "malformed.jsonl:2" in str(excinfo.value)


def test_unknown_status_is_rejected():
    with pytest.raises(RecordError, match="unknown status 'exploded'"):
        RunRecord.from_mapping(
            {
                "run_id": "r-1",
                "pipeline": "p",
                "status": "exploded",
                "duration_ms": 1,
                "owner": "o",
            }
        )


def test_missing_fields_are_listed():
    with pytest.raises(RecordError, match="missing field\\(s\\): duration_ms, owner"):
        RunRecord.from_mapping({"run_id": "r-1", "pipeline": "p", "status": "passed"})


def test_negative_duration_is_rejected():
    with pytest.raises(RecordError, match="non-negative int"):
        RunRecord.from_mapping(
            {
                "run_id": "r-1",
                "pipeline": "p",
                "status": "passed",
                "duration_ms": -1,
                "owner": "o",
            }
        )


def test_skip_bad_lines_keeps_the_parseable_ones(fixtures):
    records = load_records(fixtures / "malformed.jsonl", strict=False)

    assert [r.run_id for r in records] == ["r-20501", "r-20504"]
