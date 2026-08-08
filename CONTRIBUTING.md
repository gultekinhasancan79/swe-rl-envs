# Contributing to swe-rl-envs

Thanks for contributing. This repository treats an evaluation environment as a **measurement instrument**, not just a coding exercise. A contribution is ready when the task is reproducible, the seeded defect is demonstrably rejected, a genuinely correct fix is demonstrably accepted, and the verifier is difficult to game accidentally.

## Contribution types

Useful contributions include:

- new agentic coding environments,
- stronger held-out behavioural tests,
- verifier hardening,
- reproducibility improvements,
- adversarial evidence for benchmark-gaming attempts,
- and documentation that makes an environment easier to audit.

Small fixes to existing environments are welcome, but changes to protected tests, verifier semantics, dependency pins, or golden evidence should be treated as benchmark changes and reviewed accordingly.

## Environment contract

A new environment should follow the same trust-boundary pattern as the current `runlog-rollup` task:

```text
envs/<environment>/
├── repo/              # code visible to the agent
├── task.md            # task statement given to the agent
├── heldout/           # hidden behavioural tests + integrity material
├── verify.sh          # authoritative scorer
├── golden/            # reference solution + evidence
├── Dockerfile         # reproducible execution image
└── requirements.txt   # pinned toolchain
```

The exact filenames may evolve, but the separation between **agent-visible material**, **held-out scoring material**, and **reference evidence** must remain explicit.

## Authoring checklist

Before opening a pull request for a new or materially changed environment, verify all of the following.

### Task quality

- The task describes an observable software-engineering problem rather than revealing the implementation bug directly.
- The requested behaviour is precise enough to score objectively.
- Public APIs and compatibility constraints are stated when they matter.
- The task does not depend on internet access or undocumented external state.

### Seeded defect

- The broken state is intentional and minimal.
- At least one visible test demonstrates the reported symptom.
- The defect is not solvable only by matching fixture literals or reference-patch text.
- The failure mode is stable across repeated runs.

### Held-out evaluation

- Held-out tests exercise behaviour that a superficial visible-test-only fix can miss.
- Held-out data differs meaningfully from checked-in fixtures where appropriate.
- A correct implementation that differs from the reference patch can still pass.
- The candidate cannot read held-out material during the task.

### Integrity and anti-gaming

- Protected files are checked for modification when the benchmark relies on them.
- Added test hooks/configuration cannot silently deselect or neutralize scoring.
- Candidate source should not need to know fixture names, grader paths, or test-process internals.
- Verification resolves code from the candidate repository rather than a stale/shadow install.
- Scoring runs against a fresh, controlled environment.

### Reproducibility

- Base images are pinned by digest when containers are used.
- Runtime/test dependencies are pinned strongly enough that an old benchmark does not silently change.
- Network use is excluded from task execution and verification unless the benchmark explicitly requires it.
- Locale, timezone, line endings, and other relevant environmental inputs are controlled.
- Verification can be repeated from the repository instructions.

### Golden evidence

A reference solution should demonstrate that the benchmark accepts a genuine fix.

Include enough evidence to audit the claim, such as:

- the reference patch,
- a passing verifier transcript,
- image/toolchain/version identifiers,
- relevant hashes or digests,
- and adversarial examples showing plausible wrong fixes are rejected.

## Running the current benchmark

For `runlog-rollup`, start with:

```bash
cd envs/runlog-rollup
docker build -t runlog-rollup:1 .
golden/apply.sh /tmp/golden-candidate
```

Then run the verifier using the isolated Docker invocation documented in [`envs/runlog-rollup/README.md`](envs/runlog-rollup/README.md).

The repository's GitHub Actions workflow also executes the golden verification path on pushes and pull requests.

## Pull requests

Keep benchmark changes reviewable:

- explain **what measurement property changes**,
- identify any new or modified trust boundary,
- describe how the seeded defect fails,
- describe why the golden fix passes,
- list adversarial/partial fixes you tested,
- and call out any dependency, image, checksum, or expected-test-count changes.

Avoid mixing unrelated refactors with benchmark-semantic changes. A small, auditable diff is easier to trust than a broad cleanup bundled with scoring changes.

## Commit hygiene

Prefer focused commit messages that describe the benchmark change, for example:

- `env: add held-out regression for state leakage`
- `verifier: reject collection-time overrides`
- `docs: record golden verification evidence`

Do not commit credentials, generated caches, local virtual environments, or candidate scratch directories.

## Definition of done

A benchmark contribution is complete when:

1. the seeded/broken state is rejected,
2. the reference fix is accepted,
3. held-out tests protect the intended contract,
4. integrity gates defend the scoring boundary,
5. execution is reproducible,
6. evidence is checked in and reviewable,
7. and CI passes.
