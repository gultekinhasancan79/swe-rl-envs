"""Rendering of a :class:`~runlog.rollup.Rollup` for humans and for machines.

The text format is what gets pasted into the incident channel; the JSON format
is what the dashboard scrapes. Both are considered stable output -- changing a
column breaks somebody's grep.
"""

from __future__ import annotations

import json

from .records import VALID_STATUSES
from .rollup import FileSummary, Rollup

_COLUMNS = ("total",) + VALID_STATUSES


def format_text(rollup: Rollup) -> str:
    """Render ``rollup`` as a fixed-width table."""
    lines = ["runlog report", "=" * 13, ""]

    for summary in rollup.files:
        lines.append(summary.path)
        lines.append("  " + _counts_line(summary))
        lines.append(
            f"  duration {summary.total_duration_ms} ms"
            f" | pass rate {summary.pass_rate:.1%}"
            f" | owners {', '.join(summary.owners) or '-'}"
        )
        lines.append("")

    lines.append("OVERALL")
    lines.append(
        "  "
        + " ".join(
            f"{column}={_value(rollup, column)}" for column in _COLUMNS
        )
    )
    lines.append(
        f"  duration {rollup.total_duration_ms} ms"
        f" | pass rate {rollup.pass_rate:.1%}"
        f" | files {len(rollup.files)}"
    )
    return "\n".join(lines)


def format_json(rollup: Rollup) -> str:
    """Render ``rollup`` as JSON for the dashboard scraper."""
    payload = {
        "files": [
            {
                "path": summary.path,
                "record_count": summary.record_count,
                "status_counts": summary.status_counts,
                "total_duration_ms": summary.total_duration_ms,
                "owners": list(summary.owners),
            }
            for summary in rollup.files
        ],
        "overall": {
            "record_count": rollup.record_count,
            "status_counts": rollup.status_counts,
            "total_duration_ms": rollup.total_duration_ms,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _counts_line(summary: FileSummary) -> str:
    parts = [f"total={summary.record_count}"]
    parts += [
        f"{status}={summary.status_counts.get(status, 0)}" for status in VALID_STATUSES
    ]
    return " ".join(parts)


def _value(rollup: Rollup, column: str) -> int:
    if column == "total":
        return rollup.record_count
    return rollup.status_counts.get(column, 0)
