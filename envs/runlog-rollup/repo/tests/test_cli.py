"""End-to-end tests for the ``runlog`` command.

We shell out rather than calling ``cli.main`` in-process so that argument
parsing, exit codes and stderr are exercised the way the cron job sees them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import runlog

SRC = Path(runlog.__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(SRC))
    return subprocess.run(
        [sys.executable, "-m", "runlog", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_reports_a_single_shard(shard_a):
    result = run_cli(str(shard_a))

    assert result.returncode == 0, result.stderr
    assert "total=5 passed=3 failed=1 skipped=1 timeout=0" in result.stdout
    assert "OVERALL" in result.stdout


def test_json_format_is_machine_readable(shard_a):
    result = run_cli("--format", "json", str(shard_a))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall"]["record_count"] == 5
    assert payload["overall"]["status_counts"] == {
        "failed": 1,
        "passed": 3,
        "skipped": 1,
    }


def test_missing_file_exits_three(tmp_path):
    result = run_cli(str(tmp_path / "nope.jsonl"))

    assert result.returncode == 3
    assert "no such record file" in result.stderr


def test_bad_record_exits_two_and_names_the_line(fixtures):
    result = run_cli(str(fixtures / "malformed.jsonl"))

    assert result.returncode == 2
    assert "malformed.jsonl:2" in result.stderr


def test_skip_bad_lines_still_reports(fixtures):
    result = run_cli("--skip-bad-lines", str(fixtures / "malformed.jsonl"))

    assert result.returncode == 0, result.stderr
    assert "total=2 passed=1 failed=1 skipped=0 timeout=0" in result.stdout
