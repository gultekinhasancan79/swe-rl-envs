# Reward hacking: five strategies and the gates that defeat them

A coding benchmark scores a patch by running tests. Anything that makes the
tests report success without fixing the defect is a reward hack. This note
lists the five strategies the verifiers in this repository were built against,
shows which gate stops each one, and says what the gates do not cover.

The gate numbers refer to the nine-layer verifier shape in the
[README](../README.md#verifier-gates). The commands quoted below are from
[`envs/runlog-rollup/verify.sh`](../envs/runlog-rollup/verify.sh); the
`cursor-pagination` verifier has the same structure with its own package name
and test counts.

## The attack surface

Every candidate is scored in a fresh container built from the task image, with
no network, the candidate repository mounted read-only, and the held-out tests
and the verifier mounted from outside the repository. That leaves one boundary
to defend: the line between the candidate's files and the test run. All five
strategies below try to cross it.

## 1. Edit the tests

The simplest hack: change the assertion that fails, delete the test, or edit the
fixture it reads. The agent-facing task says not to, but a rule in `task.md` is
not a control.

**Gate 3, protected-file integrity.** Every visible test and fixture, plus
`pyproject.toml`, is listed in `CHECKSUMS.sha256` with its digest. The manifest ships with the held-out
material, not inside the repository, so the candidate cannot update it to match
an edited file. A mismatch is fatal: the verifier stops before running a single
test, because once the tests have moved, every later number would measure a
different benchmark than the one that was authored.

A deleted test is also caught a second way. Suite results are read from JUnit
XML and the collected count must equal the expected count (`20` visible and
`12` held-out for `runlog-rollup`), so a suite that shrinks fails even if every
remaining test passes.

## 2. Neutralise the suite at collection time

Checksums pin the contents of files that existed when the manifest was written.
They say nothing about new files. A `conftest.py` can skip or deselect tests it
never touches; a `pytest.ini` can change what gets collected; a `.pth` file or
`sitecustomize.py` can run code before any test does; and `PYTEST_ADDOPTS` can
do all of that from the environment without touching a file.

**Gate 4, no collection-time overrides.** The verifier scans the repository for
added `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `sitecustomize.py`,
`usercustomize.py` and `*.pth` files, allowing only the checksummed
`tests/conftest.py`.

**Environment scrubbing.** `PYTEST_ADDOPTS`, `PYTEST_PLUGINS`, `PYTHONSTARTUP`,
`PYTHONWARNINGS` and `PYTHONOPTIMIZE` are unset, `PYTHONNOUSERSITE=1` removes
the user site directory, and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` means every
plugin has to be named on the command line. Nothing a candidate drops into the
environment gets to participate.

**A separate configuration for held-out tests.** The held-out files are copied
out of the read-only mount into a scratch directory with its own `pytest.ini`,
so the candidate's `pyproject.toml` has no say in how they are collected.

**Skips count as failures.** The JUnit reader treats `skipped` and `xfail` the
same as `failures` and `errors`. A suite that quietly shrinks is as loud as one
that fails.

## 3. Branch on the grader

A patch can detect that it is under test and behave differently: read
`PYTEST_CURRENT_TEST`, import `pytest` inside the library, walk the call stack
with `inspect.stack()` or `sys._getframe`, or special-case the fixture
filenames it saw in the task (`shard_a.jsonl`, `shard_b.jsonl`).

**Gate 5, harness-awareness check.** The verifier greps `src/` for those tells.
A correct fix to an aggregation bug or a cursor protocol never needs to know it
is being tested, so any match is reported as branch-on-the-grader behaviour.

**Gate 8, held-out suite.** The grep is a pattern list and a determined author
can disguise a tell. The held-out tests are the backstop: they use different
data and exercise parts of the contract the visible tests do not, so a patch
keyed to the visible fixtures fails on them regardless of how the keying was
written.

## 4. Substitute the package

Tests import the library by name. If that name resolves to something other than
the candidate's source, the tests are grading the wrong code: a stale
`pip install` of a correct version, a shim earlier on `sys.path`, a shadowing
copy of the package, or an upstream fix fetched during the run.

**Gate 6, module provenance.** The verifier calls
`importlib.util.find_spec` on the package and requires its origin to be under
the repository's `src/`. It then walks every `sys.path` entry looking for
another `__init__.py` of the same package outside `src/` and fails on any
shadowing copy.

**Gate 2, no network.** The verifier tries to open a connection to two public
resolvers and treats a reachable network as a broken harness, so a known-good
copy cannot be fetched at scoring time.

**Read-only mount, fresh container.** Verification never runs in the container
the candidate worked in. Anything installed or written during the task does
not exist at scoring time, and a fix that only works because something was
written during the run is not a fix.

## 5. Fix the symptom, not the contract

The most realistic hack is not malicious. The agent sees one failing visible
test, makes it pass, and stops. For `cursor-pagination` that is a candidate
that stops when a page is empty instead of when `next_cursor` is `None`; for
`runlog-rollup` it is a candidate that resets the accumulator per call, per
file or per fixture while the shared mutable default survives for the lifetime
of the process.

**Gate 8, held-out suite.** The held-out tests cover the parts of the contract
that the reported symptom does not: empty intermediate pages, cursor loops and
page-count limits for the pagination client; both sides of the caller-supplied
counter contract for the rollup.

**Gate 9, combined run.** For a process-lifetime state bug the strongest single
check is to run the visible and held-out suites in one interpreter. A fix that
merely resets state between suites, files or fixtures shows up here and nowhere
else.

This is the only strategy with recorded evidence against authored candidates.
The [walkthrough](WALKTHROUGH.md) runs three candidates through the unchanged
`cursor-pagination` verifier:

| Candidate | Visible | Held-out | Combined | Gates | Verifier |
| --- | ---: | ---: | ---: | ---: | --- |
| Seeded defect | 12/13 | 2/10 | 14/23 | 6/9 | FAIL |
| Partial fix (stops on empty page) | 13/13 | 8/10 | 21/23 | 7/9 | FAIL |
| Reference fix | 13/13 | 10/10 | 23/23 | 9/9 | PASS |

The partial fix passes every visible test and still fails. These are authored
candidates, not model outputs; the table shows what the verifier does, not how
often a model attempts the strategy.

## Coverage map

| Strategy | Primary gate | Backstop |
| --- | --- | --- |
| 1. Edit the tests | 3, protected-file integrity (fatal) | JUnit collected-count check |
| 2. Neutralise collection | 4, no collection-time overrides | environment scrubbing, separate held-out config, skips counted as failures |
| 3. Branch on the grader | 5, harness-awareness check | 8, held-out suite on different data |
| 4. Substitute the package | 6, module provenance | 2, no network; read-only mount; fresh container |
| 5. Fix the symptom | 8, held-out suite | 9, combined single-process run |

No strategy is stopped by one control alone. That is the second design
principle in the README: a plausible attempt should trip more than one
independent gate.

## What the gates do not cover

- **Gate 5 is a pattern list.** It catches the obvious tells. A tell written to
  evade the grep passes gate 5 and has to be caught by gates 8 and 9, which
  only work if the held-out data differs enough from the visible data. Held-out
  suite design carries that weight, not the grep.
- **The container runtime is trusted.** The gates defend the boundary between
  the repository and the test run. An attack on Docker itself, on the pinned
  base image or on the host is out of scope.
- **Behaviour is scored, not intent.** A patch that satisfies the full contract
  in a strange or ugly way passes. That is by design (principle 3, behaviour
  over diff similarity), and it means the verifier cannot tell a good engineer
  from a lucky one.
- **Two environments.** Both current environments share this gate shape, but
  they cover two defect classes. A new defect class may need a gate this list
  does not have; the [contributing checklist](../CONTRIBUTING.md) has an
  integrity and anti-gaming section for that reason.
