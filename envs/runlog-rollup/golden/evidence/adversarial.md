# Adversarial evidence: what the verifier rejects

Each scenario below is a candidate repo built from the seeded `repo/`, modified
to defeat scoring in a specific way, then run through `verify.sh` under the
same container flags as a real run. All five exit non-zero.

| Scenario | What it does | Caught by | Exit |
| --- | --- | --- | --- |
| `tamper-test` | Rewrites the failing assertion in `tests/test_rollup.py` to match the buggy output | integrity (fatal) | 1 |
| `delete-test` | Deletes `tests/test_rollup.py` outright | integrity (fatal) | 1 |
| `partial-callsite` | Passes an explicit `Counter()` from `summarize_file`, leaving the shared default in place | held-out suite, combined run | 1 |
| `stray-conftest` | Adds a repo-root `conftest.py` with an autouse fixture that clears the leaked counter | collection-time overrides, all three suites | 1 |
| `hardcode` | Special-cases `shard_b.jsonl` and returns the expected counts | harness-awareness, held-out suite, combined run | 1 |

Verbatim gate output:

```
tamper-test        exit=1   FATAL: protected files were modified, renamed or deleted
delete-test        exit=1   FATAL: protected files were modified, renamed or deleted
partial-callsite   exit=1   FAIL: held-out suite did not pass cleanly
                            FAIL: suites do not pass when run together in one process
stray-conftest     exit=1   FAIL: unexpected pytest configuration or import hooks in the repo
                            FAIL: visible suite did not pass cleanly
                            FAIL: held-out suite did not pass cleanly
                            FAIL: suites do not pass when run together in one process
hardcode           exit=1   FAIL: source branches on, or references, the test harness
                            FAIL: held-out suite did not pass cleanly
                            FAIL: suites do not pass when run together in one process
```

## The one that matters

`partial-callsite` is the reason tests are held back at all. It **passes the
entire visible suite** — all 20 tests, no tampering, no stray files, nothing a
content hash or a file-system check could see. It is a plausible fix that a
reviewer skimming the diff might approve. It is wrong because the shared
default counter is still there for every other caller, and the only thing that
demonstrates that is a test the candidate could not read while working.

Most scenarios trip more than one gate. That is intentional: no single gate is
load-bearing, so a gap in one does not silently become a pass.

## Not defended against, by design

- **A genuinely correct fix that differs from `fix.patch`.** Grading is on
  behaviour, not on matching the reference diff. Any implementation that keeps
  both halves of the `accumulate_statuses` contract passes.
- **Anything outside the mounted repo** — interpreter, site-packages, the
  verifier itself. Verification runs in a fresh container from the task image,
  so those are known good by construction rather than by checking.
