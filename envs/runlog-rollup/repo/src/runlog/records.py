"""Parsing for run-record files.

Record files are newline-delimited JSON: one object per line, as written by
the job runners in ``platform/runner``. Blank lines are ignored so that files
concatenated by ``cat`` stay readable.

Malformed lines raise :class:`RecordError` with the file and line number, which
is what the on-call rotation actually needs when a runner ships bad output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

#: Statuses the runners are allowed to emit. Anything else is a bug upstream
#: and we would rather fail loudly than silently bucket it.
VALID_STATUSES = ("passed", "failed", "skipped", "timeout")

_REQUIRED_FIELDS = ("run_id", "pipeline", "status", "duration_ms", "owner")


class RecordError(ValueError):
    """A line in a record file could not be turned into a :class:`RunRecord`."""

    def __init__(self, path: str | Path, lineno: int, message: str) -> None:
        self.path = str(path)
        self.lineno = lineno
        super().__init__(f"{self.path}:{lineno}: {message}")


@dataclass(frozen=True)
class RunRecord:
    """One pipeline run, as reported by a runner."""

    run_id: str
    pipeline: str
    status: str
    duration_ms: int
    owner: str

    @classmethod
    def from_mapping(
        cls, data: Any, *, path: str | Path = "<memory>", lineno: int = 0
    ) -> "RunRecord":
        if not isinstance(data, dict):
            raise RecordError(path, lineno, "expected a JSON object")

        missing = [f for f in _REQUIRED_FIELDS if f not in data]
        if missing:
            raise RecordError(path, lineno, f"missing field(s): {', '.join(missing)}")

        status = data["status"]
        if status not in VALID_STATUSES:
            raise RecordError(path, lineno, f"unknown status {status!r}")

        duration = data["duration_ms"]
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
            raise RecordError(
                path, lineno, f"duration_ms must be a non-negative int, got {duration!r}"
            )

        return cls(
            run_id=str(data["run_id"]),
            pipeline=str(data["pipeline"]),
            status=status,
            duration_ms=duration,
            owner=str(data["owner"]),
        )


def iter_records(path: str | Path) -> Iterator[RunRecord]:
    """Yield every record in ``path``, raising on the first bad line."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RecordError(path, lineno, f"invalid JSON: {exc.msg}") from exc
            yield RunRecord.from_mapping(data, path=path, lineno=lineno)


def load_records(path: str | Path, *, strict: bool = True) -> list[RunRecord]:
    """Read ``path`` into a list of records.

    With ``strict=False`` bad lines are dropped instead of raising, which is how
    the nightly cron calls us -- one corrupt line should not lose the report.
    """
    if strict:
        return list(iter_records(path))

    records: list[RunRecord] = []
    iterator = iter_records(path)
    while True:
        try:
            records.append(next(iterator))
        except StopIteration:
            return records
        except RecordError:
            # Non-strict mode: skip the bad line and keep going. ``iter_records``
            # is a generator, so it is dead after raising -- reopen and resume.
            records.extend(_resume_after_error(path, len(records)))
            return records


def _resume_after_error(path: str | Path, already_read: int) -> list[RunRecord]:
    """Best-effort recovery: re-scan ``path`` keeping only parseable lines."""
    good: list[RunRecord] = []
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                good.append(
                    RunRecord.from_mapping(json.loads(line), path=path, lineno=lineno)
                )
            except (RecordError, json.JSONDecodeError):
                continue
    return good[already_read:]
