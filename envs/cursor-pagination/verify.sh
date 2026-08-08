#!/usr/bin/env bash
# Verifier for the cursor-pagination evaluation environment.

set -uo pipefail

REPO="${REPO:-/work/repo}"
HELDOUT="${HELDOUT:-/verify/heldout}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

EXPECTED_VISIBLE_TESTS=13
EXPECTED_HELDOUT_TESTS=10

export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
export PYTHONHASHSEED=0
export PYTHONPATH="$REPO/src"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
unset PYTHONSTARTUP PYTEST_ADDOPTS PYTEST_PLUGINS PYTHONWARNINGS PYTHONOPTIMIZE 2>/dev/null

PYTEST_BASE=(-p pytest_timeout -p no:cacheprovider --timeout=120 --timeout-method=thread)

FAILURES=0
STEP=0

step()  { STEP=$((STEP + 1)); printf '\n=== [%d] %s\n' "$STEP" "$1"; }
ok()    { printf '    ok: %s\n' "$1"; }
fail()  { printf '    FAIL: %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
die()   { printf '\n    FATAL: %s\n' "$1"; printf '\nRESULT: FAIL\n'; exit 1; }

printf 'cursor-pagination verifier\n'
printf 'repo:    %s\n' "$REPO"
printf 'heldout: %s\n' "$HELDOUT"
printf 'python:  %s\n' "$(python -V 2>&1)"
printf 'pytest:  %s\n' "$(python -m pytest --version 2>&1 | head -1)"

step "Preflight"
[ -d "$REPO/src/pagewalk" ] || die "no pagewalk package at $REPO/src/pagewalk"
[ -r "$HELDOUT/CHECKSUMS.sha256" ] || die "held-out manifest not mounted"
ls "$HELDOUT"/test_*.py >/dev/null 2>&1 || die "no held-out tests mounted"
ok "repo and held-out material present"

step "No network"
if python - <<'PY'
import socket, sys
for addr in (("1.1.1.1", 53), ("8.8.8.8", 53)):
    try:
        socket.create_connection(addr, timeout=2).close()
        sys.exit(0)
    except OSError:
        continue
sys.exit(1)
PY
then
    die "network is reachable -- re-run with --network none"
fi
ok "no egress"

step "Visible test files unchanged"
if ! (cd "$REPO" && sha256sum -c --quiet "$HELDOUT/CHECKSUMS.sha256"); then
    printf '\n    expected digests:\n'
    sed 's/^/      /' "$HELDOUT/CHECKSUMS.sha256"
    die "protected files were modified, renamed or deleted"
fi
ok "$(wc -l < "$HELDOUT/CHECKSUMS.sha256") protected files match their recorded digests"

step "No collection-time overrides"
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
    ok "no added collection-time overrides"
fi

step "Source is unaware of the test harness"
TELLS="$(grep -rnE 'PYTEST_CURRENT_TEST|import pytest|unittest|inspect\.stack|sys\._getframe|short_intermediate|after-filter|cursor-a|tests/' \
    "$REPO/src" 2>/dev/null)"
if [ -n "$TELLS" ]; then
    printf '%s\n' "$TELLS" | sed 's/^/      /'
    fail "source branches on, or references, grader/test details"
else
    ok "no test-harness awareness in src/"
fi

step "Module provenance"
if python - "$REPO" <<'PY'
import importlib.util, pathlib, sys

repo_src = pathlib.Path(sys.argv[1], "src").resolve()
problems = []
spec = importlib.util.find_spec("pagewalk")
if spec is None or not spec.origin:
    problems.append("pagewalk is not importable")
else:
    origin = pathlib.Path(spec.origin).resolve()
    if repo_src not in origin.parents:
        problems.append(f"pagewalk resolves to {origin}, outside {repo_src}")
    others = [
        p
        for entry in sys.path
        if entry
        for p in pathlib.Path(entry).glob("pagewalk/__init__.py")
        if repo_src not in p.resolve().parents
    ]
    if others:
        problems.append(f"shadowing copies on sys.path: {others}")

for problem in problems:
    print(problem)
sys.exit(1 if problems else 0)
PY
then
    ok "pagewalk imports from the repo under test only"
else
    fail "pagewalk is not being imported from the repo under test"
fi

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

step "Visible suite"
(cd "$REPO" && python -m pytest "${PYTEST_BASE[@]}" \
    --junit-xml="$WORK/visible.xml" -q)
if [ -f "$WORK/visible.xml" ] && DETAIL="$(assert_junit "$WORK/visible.xml" "$EXPECTED_VISIBLE_TESTS")"; then
    ok "visible suite: $EXPECTED_VISIBLE_TESTS passed"
else
    printf '%s\n' "${DETAIL:-no report produced}" | sed 's/^/      /'
    fail "visible suite did not pass cleanly"
fi

step "Held-out suite"
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

step "Both suites in one process"
(cd "$WORK" && python -m pytest "${PYTEST_BASE[@]}" \
    --junit-xml="$WORK/combined.xml" -q "$REPO/tests" "$WORK")
COMBINED_TESTS=$((EXPECTED_VISIBLE_TESTS + EXPECTED_HELDOUT_TESTS))
if [ -f "$WORK/combined.xml" ] && DETAIL="$(assert_junit "$WORK/combined.xml" "$COMBINED_TESTS")"; then
    ok "combined run: $COMBINED_TESTS passed in a single interpreter"
else
    printf '%s\n' "${DETAIL:-no report produced}" | sed 's/^/      /'
    fail "visible and held-out suites do not pass together"
fi

printf '\n=== summary\n'
if [ "$FAILURES" -eq 0 ]; then
    printf '\nRESULT: PASS\n'
    exit 0
fi
printf '    %d gate(s) failed\n' "$FAILURES"
printf '\nRESULT: FAIL\n'
exit 1
