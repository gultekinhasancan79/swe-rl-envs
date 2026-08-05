"""runlog -- summarize pipeline run-record files into one report."""

from __future__ import annotations

__version__ = "0.4.2"

from .records import RecordError, RunRecord, load_records
from .rollup import FileSummary, Rollup, accumulate_statuses, build_rollup, summarize_file

__all__ = [
    "FileSummary",
    "RecordError",
    "Rollup",
    "RunRecord",
    "accumulate_statuses",
    "build_rollup",
    "load_records",
    "summarize_file",
]
