# runlog-rollup — agentic coding evaluation environment

A single, self-contained task for benchmarking coding agents. The agent is
given a small internal CLI tool with one seeded defect and a failing test, and
is scored by a verifier it never sees.

**The defect:** `runlog.rollup.accumulate_statuses` declares its accumulator as
a mutable default argument, so every call that omits it tallies into one
`Counter` created at import time. The first file processed in a process is
correct; every file after it inherits the previous file's counts. The failing
test reports a count mismatch and nothing else.

## Layout

```
Dockerfile            digest-pinned image; contains repo/ and nothing else
requirements.txt      hash-pinned test toolchain
task.md               what the agent is given
verify.sh             the verifier; bind-mounted at scoring time
repo/                 ── the agent sees this ──
  src/runlog/         the tool
  tests/              visible suite: 19 pass, 1 fails
heldout/              ── the agent never sees this ──
  test_heldout_rollup.py    12 acceptance tests
  CHECKSUMS.sha256          digests of the visible tests and fixtures
golden/               ── reference solution ──
  fix.patch, apply.sh, NOTES.md, evidence/
```

The directory split is the trust boundary. Only `repo/` and `requirements.txt`
can enter the image — `.dockerignore` denies everything by default and
re-allows those two. `verify.sh` and `heldout/` are bind-mounted read-only in a
separate container at scoring time, so they are not on disk while the agent
works and cannot be read, edited or pre-satisfied.

## The contract

**What the agent gets:** `task.md`, a checkout of `repo/`, and a container with
the toolchain preinstalled and no network.

**What the agent may change:** anything under `repo/src/`. Nothing else.
`task.md` states this in plain language, and `verify.sh` enforces it.

**How it is scored:** a fresh container from the task image, with the candidate
repo mounted **read-only**:

```sh
docker build -t runlog-rollup:1 .

docker run --rm --network none \
  --read-only --tmpfs /tmp:rw,exec,nosuid,size=256m \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --pids-limit 256 \
  -v "$PWD/candidate:/work/repo:ro" \
  -v "$PWD/heldout:/verify/heldout:ro" \
  -v "$PWD/verify.sh:/verify/verify.sh:ro" \
  runlog-rollup:1 bash /verify/verify.sh
```

Verification never reuses the container the agent worked in. Everything outside
the mounted repo is therefore known good by construction, and the gates only
have to defend one boundary.

`verify.sh` prints `RESULT: PASS` and exits 0, or `RESULT: FAIL` and exits 1.
It is the only signal; there is no partial credit.

## The nine gates

| # | Gate | Stops |
| - | ---- | ----- |
| 1 | Preflight | A misconfigured harness scoring nothing |
| 2 | No network | A solution fetched from the internet |
| 3 | Visible files unchanged (sha256) | Editing or deleting the failing test or its fixtures |
| 4 | No collection-time overrides | An added `conftest.py`, `pytest.ini` or `.pth` neutralising a suite |
| 5 | Source unaware of the harness | Branching on `PYTEST_CURRENT_TEST` or naming fixture files |
| 6 | Module provenance | `runlog` resolving to a shim or a stale install |
| 7 | Visible suite | The reported bug |
| 8 | Held-out suite | Fixes that satisfy only what the agent could read |
| 9 | Both suites in one process | Fixes that reset state per suite or per file |

Gates 3–6 are integrity checks, 7–9 are behavioural. Gate 3 is fatal: if the
tests moved, everything downstream is measuring a different benchmark.

Test counts come from JUnit XML, not from scraping pytest's summary, so a suite
that silently shrinks — `skipif`, `xfail`, a deselect — fails as loudly as one
that errors. Plugin autoloading is disabled and every plugin named explicitly,
and `PYTEST_ADDOPTS` and friends are unset before anything runs.

## Reproducibility

- **Base image pinned by digest**, not by tag. `python:3.12-slim` is rebuilt
  whenever Debian ships a security update; a tag pin would silently change the
  interpreter patch level between authoring and scoring.
- **Every dependency, direct and transitive, pinned with a sha256** and
  installed with `--require-hashes --no-deps`. Adding a package without its
  hash fails the build instead of drifting.
- **The network is used exactly once**, at image build time. Task execution and
  verification both run with `--network none`, and gate 2 fails if egress is
  somehow reachable.
- **`PYTHONDONTWRITEBYTECODE`, `PYTHONHASHSEED=0`, `PYTHONNOUSERSITE`, `TZ=UTC`,
  `LC_ALL=C.UTF-8`** are set in the image, so no stale bytecode, locale or
  user-site package can change a result.
- **`.gitattributes` forces LF.** The checksums are over bytes; a CRLF checkout
  would fail gate 3 for no reason.

## Why the visible suite fails exactly once

A process-lifetime accumulator leaks into *every* subsequent call, so a naive
test suite would fail in a scattered, order-dependent way — and "results change
depending on what else ran" hands the agent the answer.

Exactly one visible test exercises the file→counts path in-process. The rest
avoid it honestly: `test_cli.py` shells out to a subprocess, `test_report.py`
builds `Rollup` values directly, `test_records.py` never reaches aggregation,
and the remaining `test_rollup.py` cases pass an explicit accumulator, which is
immune. The failure is therefore byte-identical whether you run one test, one
file, or the whole suite.

## Maintenance

Changing anything under `repo/tests/` or `repo/pyproject.toml` invalidates the
manifest. Regenerate it from inside the image, which is the ground truth:

```sh
docker build -t runlog-rollup:1 .
docker run --rm --network none runlog-rollup:1 \
  bash -c 'cd /work/repo && sha256sum pyproject.toml tests/conftest.py \
    tests/test_*.py tests/fixtures/*.jsonl' > heldout/CHECKSUMS.sha256
```

Adding or removing tests also means updating `EXPECTED_VISIBLE_TESTS` /
`EXPECTED_HELDOUT_TESTS` at the top of `verify.sh`. After any change, re-run
the golden solution and confirm it still passes:

```sh
golden/apply.sh /tmp/golden-candidate     # then the docker run above
```

Evidence for the current state is in `golden/evidence/`: `verify.log` (the full
passing transcript), `run.md` (image ID, versions, digests) and
`adversarial.md` (five defeat attempts, all rejected).
