# runlog

Summarizes pipeline run-record files into one report.

The job runners in `platform/runner` write one newline-delimited JSON file per
shard. `runlog` reads those files and prints a per-shard breakdown plus overall
totals — the thing that gets pasted into `#ops-nightly` every morning and
scraped by the reliability dashboard.

## Usage

```
python -m runlog shard-*.jsonl
python -m runlog --format json shard-a.jsonl shard-b.jsonl
python -m runlog --skip-bad-lines shard-a.jsonl
```

Exit codes: `0` ok, `2` unparseable record, `3` missing file.

## Record format

```json
{"run_id": "r-20418", "pipeline": "nightly-etl", "status": "passed", "duration_ms": 84120, "owner": "data-platform"}
```

`status` must be one of `passed`, `failed`, `skipped`, `timeout`. Anything else
is a runner bug and we fail loudly rather than bucket it silently.

## Layout

| Path                | What it does                                  |
| ------------------- | --------------------------------------------- |
| `src/runlog/records.py` | Parsing and validation of record files    |
| `src/runlog/rollup.py`  | Aggregation into per-file and overall totals |
| `src/runlog/report.py`  | Text and JSON rendering                   |
| `src/runlog/cli.py`     | Argument parsing and exit codes           |

## Tests

```
PYTHONPATH=src python -m pytest
```

Both output formats are considered stable — changing a column breaks
somebody's grep.
