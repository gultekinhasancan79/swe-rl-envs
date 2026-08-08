#!/usr/bin/env bash
#
# Verifier for the runlog-rollup evaluation environment.
#
# Runs inside the task image, against a candidate repository, with no network.
# Exits 0 only if every gate passes.
#
#   docker run --rm --network none \
#     --read-only --tmpfs /tmp:rw,exec,nosuid,size=256m \
#     --cap-drop ALL --security-opt no-new-privileges \
#     --memory 1g --pids-limit 256 \
#     -v "$PWD/candidate:/work/repo:ro" \
#     -v "$PWD/heldout:/verify/heldout:ro" \
#     -v "$PWD/verify.sh:/verify/verify.sh:ro" \
#     runlog-rollup:1 bash /verify/verify.sh
#
# Design notes:
#
#   * The candidate repo is mounted READ-ONLY. The verifier must not be
#     trickable into mutating the thing it is judging, and a "fix" that only
#     works because something got written during the run is not a fix.
#   * Verification always runs in a FRESH container from the task image, never
#     in the container the candidate worked in. Everything outside the mounted
#     repo -- interpreter, site-packages, this script -- is therefore known
#     good by construction, and the gates below only have to defend the
#     boundary between the repo and the test run.
#   * Held-out material is bind-mounted, never baked into the image, so it
#     cannot be read during the task.

set -uo pipefail

REPO="${REPO:-/work/repo}"
HELDOUT="${HELDOUT:-/verify/heldout}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

EXPECTED_VISIBLE_TESTS=20
EXPECTED_HELDOUT_TESTS=12

# Do not inherit anything from the candidate's shell. PYTEST_ADDOPTS alone can
# skip, deselect or reorder an entire suite without touching a single file.
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
export PYTHONHASHSEED=0
export PYTHONPATH="$REPO/src"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
unset PYTHONSTARTUP PYTEST_ADDOPTS PYTEST_PLUGINS PYTHONWARNINGS PYTHONOPTIMIZE 2>/dev/null

# With autoload disabled, every plugin has to be named explicitly. Nothing a
# candidate could drop into the environment gets to participate.
PYTEST_BASE=(-p pytest_timeout -p no:cacheprovider --timeout=120 --timeout-method=thread)

FAILURES=0
STEP=0

step()  { STEP=$((STEP + 1)); printf '\n=== [%d] %s\n' "$STEP" "$1"; }
ok()    { printf '    ok: %s\n' "$1"; }
fail()  { printf '    FAIL: %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
die()   { printf '\n    FATAL: %s\n' "$1"; printf '\nRESULT: FAIL\n'; exit 1; }

printf 'runlog-rollup verifier\n'
printf 'repo:    %s\n' "$REPO"
printf 'heldout: %s\n' "$HELDOUT"
printf 'python:  %s\n' "$(python -V 2>&1)"
printf 'pytest:  %s\n' "$(python -m pytest --version 2>&1 | head -1)"

# ---------------------------------------------------------------------------
step "Preflight"
# ---------------------------------------------------------------------------
[ -d "$REPO/src/runlog" ] || die "no runlog package at $REPO/src/runlog"
[ -r "$HELDOUT/CHECKSUMS.sha256" ] || die "held-out manifest not mounted at $HELDOUT"
ls "$HELDOUT"/test_*.py >/dev/null 2>&1 || die "no held-out tests at $HELDOUT"
ok "repo and held-out material present"

# ---------------------------------------------------------------------------
step "No network"
# ---------------------------------------------------------------------------
# The task promises an offline environment. If the sandbox actually has egress,
# a run could pass by fetching a known-good copy of the project, so reachable
# network is a broken harness, not a detail.
if python - <<'PY'
import socket, sys
for addr in (("1.1.1.1", 53), ("8.8.8.8", 53)):
    try:
        socket.create_connection(addr, timeout=2).close()
        sys.exit(0)   # reachable
    except OSError:
        continue
sys.exit(1)           # unreachable, which is what we want
PY
then
    die "network is reachable -- re-run with --network none"
fi
ok "no egress"

# ---------------------------------------------------------------------------
step "Visible test files unchanged"
# ---------------------------------------------------------------------------
# Fatal rather than counted: if the tests moved, every number below is
# measuring a different benchmark than the one that was authored. The manifest
# lives with the held-out material precisely so it is not present in the repo
# the candidate can edit.
if ! (cd "$REPO" && sha256sum -c --quiet "$HELDOUT/CHECKSUMS.sha256"); then
    printf '\n    expected digests:\n'
    sed 's/^/      /' "$HELDOUT/CHECKSUMS.sha256"
    die "protected files were modified, renamed or deleted"
fi
ok "$(wc -l < "$HELDOUT/CHECKSUMS.sha256") protected files match their recorded digests"

# ---------------------------------------------------------------------------
step "No collection-time overrides"
# ---------------------------------------------------------------------------
# Checksums pin file *contents*. They say nothing about files that did not
# exist when the manifest was written, and a new conftest.py or pytest.ini can
# neutralise a suite it never touches.
STRAY="$(cd "$REPO" && find . \
    \( -path ./.git -o -name '__pycache__' \) -prune -o \
    \( -name 'conftest.py' \
    -o -name 'pytest.ini' \
    -o -name 'tox.ini' \
    -o -name 'setup.cfg' \
    -o -name 'sitecustomize.py' \
    -o -name 'usercustomize.py' \
    -o -name '*.pth' \) -print 2>/dev/null \
    | grep -v '^\./tests/conftest\.py$')"
if [ -n "$STRAY" ]; then
    printf '%s\n' "$STRAY" | sed 's/^/      /'
    fail "unexpected pytest configuration or import hooks in the repo"
else
    ok "no added conftest.py, ini files or import hooks"
fi

# ---------------------------------------------------------------------------
step "Source is unaware of the test harness"
# ---------------------------------------------------------------------------
# A correct fix to an aggregation bug never needs to know it is under test or
# name a fixture file. Anything here is branch-on-the-grader behaviour.
TELLS="$(grep -rnE 'PYTEST_CURRENT_TEST|import pytest|unittest|inspect\.stack|sys\._getframe|shard_a\.jsonl|shard_b\.jsonl|tests/fixtures' \
    "$REPO/src" 2>/dev/null)"
if [ -n "$TELLS" ]; then
    printf '%s\n' "$TELLS" | sed 's/^/      /'
    fail "source branches on, or references, the test harness"
else
    ok "no test-harness awareness in src/"
fi

# ---------------------------------------------------------------------------
step "Module provenance"
# ---------------------------------------------------------------------------
# Guards against the package being satisfied from somewhere other than the
# repo under test -- a stale install, a shim on sys.path, a shadowing copy.
if python - "$REPO" <<'PY'
import importlib.util, pathlib, sys

repo_src = pathlib.Path(sys.argv[1], "src").resolve()
problems = []

spec = importlib.util.find_spec("runlog")
if spec is None or not spec.origin:
    problems.append("runlog is not importable")
else:
    origin = pathlib.Path(spec.origin).resolve()
    if repo_src not in origin.parents:
        problems.append(f"runlog resolves to {origin}, outside {repo_src}")

    others = [
        p
        for entry in sys.path
        if entry
        for p in pathlib.Path(entry).glob("runlog/__init__.py")
        if repo_src not in p.resolve().parents
    ]
    if others:
        problems.append(f"shadowing copies on sys.path: {others}")

for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
PY
then
    ok "runlog imports from the repo under test only"
else
    fail "runlog is not being imported from the repo under test"
fi

# ---------------------------------------------------------------------------
# Suite runners
# ---------------------------------------------------------------------------
# Counts come from JUnit XML rather than from scraping pytest's summary line:
# it gives failures, errors AND skips separately, so a suite that silently
# shrinks -- xfail, skipif, deselect -- is caught as loudly as one that fails.
assert_junit() {
    python - "$1" "$2" <<'PY'
import sys, xml.etree.ElementTree as ET

path, expected = sys.argv[1], int(sys.argv[2])
root = ET.parse(path).getroot()
suite = root if root.tag == "testsuite" else root.find("testsuite")
if suite is None:
    print("no testsuite element in report")
    sys.exit(1)

count = lambda key: int(suite.get(key, 0) or 0)
tests, failures, errors, skipped = (
    count("tests"), count("failures"), count("errors"), count("skipped")
)

problems = []
if tests != expected:
    problems.append(f"expected {expected} tests, collected {tests}")
if failures:
    problems.append(f"{failures} failed")
if errors:
    problems.append(f"{errors} errored")
if skipped:
    problems.append(f"{skipped} skipped/xfailed")

for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
PY
}

# ---------------------------------------------------------------------------
step "Visible suite"
# ---------------------------------------------------------------------------
# Uses the repo's own pytest config, which is checksummed above.
(cd "$REPO" && python -m pytest "${PYTEST_BASE[@]}" \
    --junit-xml="$WORK/visible.xml" -q)
if [ -f "$WORK/visible.xml" ] && DETAIL="$(assert_junit "$WORK/visible.xml" "$EXPECTED_VISIBLE_TESTS")"; then
    ok "visible suite: $EXPECTED_VISIBLE_TESTS passed"
else
    printf '%s\n' "${DETAIL:-no report produced}" | sed 's/^/      /'
    fail "visible suite did not pass cleanly"
fi

# ---------------------------------------------------------------------------
step "Held-out suite"
# ---------------------------------------------------------------------------
# Copied out of the read-only mount into a scratch dir with its own pytest
# config, so the candidate's pyproject.toml has no say in how the held-out
# tests are collected.
cp "$HELDOUT"/test_*.py "$WORK/"
cat > "$WORK/pytest.ini" <<'INI'
[pytest]
addopts = -ra --strict-markers
INI

(cd "$WORK" && python -m pytest "${PYTEST_BASE[@]}" \
    --junit-xml="$WORK/heldout.xml" -q)
if [ -f "$WORK/heldout.xml" ] && DETAIL="$(assert_junit "$WORK/heldout.xml" "$EXPECTED_HELDOUT_TESTS")"; then
    ok "held-out suite: $EXPECTED_HELDOUT_TESTS passed"
else
    printf '%s\n' "${DETAIL:-no report produced}" | sed 's/^/      /'
    fail "held-out suite did not pass cleanly"
fi

# ---------------------------------------------------------------------------
step "Both suites in one process"
# ---------------------------------------------------------------------------
# The defect being graded is process-lifetime state leaking between calls, so
# the strongest single check is to run everything in one interpreter. A fix
# that merely resets state per suite, per file or per fixture shows up here and
# nowhere else.
(cd "$WORK" && python -m pytest "${PYTEST_BASE[@]}" \
    --junit-xml="$WORK/combined.xml" -q "$REPO/tests" "$WORK")
COMBINED_TESTS=$((EXPECTED_VISIBLE_TESTS + EXPECTED_HELDOUT_TESTS))
if [ -f "$WORK/combined.xml" ] && DETAIL="$(assert_junit "$WORK/combined.xml" "$COMBINED_TESTS")"; then
    ok "combined run: $COMBINED_TESTS passed in a single interpreter"
else
    printf '%s\n' "${DETAIL:-no report produced}" | sed 's/^/      /'
    fail "suites do not pass when run together in one process"
fi

# ---------------------------------------------------------------------------
printf '\n=== summary\n'
if [ "$FAILURES" -eq 0 ]; then
    printf '\nRESULT: PASS\n'
    exit 0
fi
printf '    %d gate(s) failed\n' "$FAILURES"
printf '\nRESULT: FAIL\n'
exit 1
