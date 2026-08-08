<h1 align="center">swe-rl-envs</h1>

<p align="center">
  Reproducible evaluation environments for agentic coding benchmarks.
</p>

<p align="center">
  <a href="https://github.com/gultekinhasancan79/swe-rl-envs/actions/workflows/benchmark-ci.yml"><img src="https://github.com/gultekinhasancan79/swe-rl-envs/actions/workflows/benchmark-ci.yml/badge.svg" alt="Benchmark CI"></a>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Docker-Isolated%20Evaluation-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Pytest-Held--out%20Tests-0A9EDC?logo=pytest&logoColor=white" alt="Pytest">
  <img src="https://img.shields.io/badge/Scoring-Behaviour%20Based-6f42c1" alt="Behaviour-based scoring">
  <img src="https://img.shields.io/badge/Reproducibility-Digest%20Pinned-2ea44f" alt="Reproducibility">
</p>

---

## What This Repository Is

`swe-rl-envs` contains small, self-contained coding environments designed to evaluate software-engineering agents under controlled and reproducible conditions.

Each environment includes:

- a compact codebase,
- a deliberately seeded defect,
- an agent-facing task statement,
- a visible test suite,
- held-out acceptance tests the agent never sees,
- a verifier with layered integrity and behavioural gates,
- and a reference solution with reproducibility evidence.

The central requirement is simple:

> A useful benchmark must reject the seeded defect while accepting any genuinely correct fix.

Scoring is therefore based on **behaviour**, not similarity to a reference diff.

## Why This Matters

Coding-agent benchmarks are easy to make accidentally gameable.

A candidate patch can appear correct by:

- changing or deleting visible tests,
- exploiting pytest configuration,
- hard-coding known fixture values,
- branching on the test harness,
- fixing only the visible call site,
- or relying on environment drift.

These environments are built to make those failure modes observable and reproducible.

## Current Environment

| Environment | Seeded defect | Visible tests | Held-out tests | Verifier gates |
| --- | --- | ---: | ---: | ---: |
| [`runlog-rollup`](envs/runlog-rollup) | Shared mutable default accumulator leaks state across calls | 20 | 12 | 9 |

### `runlog-rollup`

The current task presents an internal record-rollup CLI whose aggregation state leaks across calls because of a mutable default argument.

The visible suite exposes the reported symptom, while the held-out suite tests the broader public contract so that a superficial call-site fix does not pass.

The verifier then evaluates the candidate through integrity and behavioural checks, including a combined single-process run specifically designed to expose process-lifetime state leakage.

## Evaluation Model

```text
Agent receives
├── task.md
├── repo/
└── pinned toolchain

Agent does NOT receive
├── heldout/
└── verifier internals during the task

Candidate patch
    ↓
Fresh isolated container
    ↓
Integrity gates
    ↓
Visible tests
    ↓
Held-out tests
    ↓
Combined behavioural run
    ↓
PASS / FAIL
```

## Design Principles

### 1. Held-out behavioural tests

Visible tests are not enough when a partial implementation can satisfy the reported symptom without restoring the real contract.

The held-out suite uses different runtime-generated data and validates behaviours the candidate cannot infer from a single checked-in fixture.

### 2. Layered gates

No single integrity check is treated as load-bearing. Most benchmark-gaming attempts should trip more than one independent gate.

### 3. Behaviour over diff similarity

The verifier does not require the candidate patch to resemble the golden patch. Any implementation that satisfies the intended contract is allowed to pass.

### 4. Reproducible execution

The environment pins important execution inputs so that results do not silently change over time:

- base image by digest,
- direct and transitive Python dependencies by version and SHA-256,
- deterministic interpreter settings,
- no network during task execution or verification,
- controlled locale/timezone,
- normalized line endings,
- and a fresh verification container.

### 5. Explicit trust boundary

The candidate repository is mounted read-only during scoring. Held-out tests and the verifier are supplied separately, so the scoring boundary is defined by construction rather than by assuming the candidate did not modify external state.

## Verifier Gates

The current `runlog-rollup` environment uses nine gates:

| # | Gate | Purpose |
| ---: | --- | --- |
| 1 | Preflight | Reject a broken or incomplete harness |
| 2 | No network | Ensure execution remains offline |
| 3 | Protected-file integrity | Reject modified/deleted visible tests and fixtures |
| 4 | No collection-time overrides | Detect added pytest/import hooks |
| 5 | Harness-awareness check | Detect source code branching on grader details |
| 6 | Module provenance | Ensure the package resolves from the candidate repo |
| 7 | Visible suite | Validate the reported task behaviour |
| 8 | Held-out suite | Validate unseen parts of the contract |
| 9 | Combined process run | Expose fixes that only reset state between suites/files |

## Evidence

The repository includes reviewable evidence under:

```text
envs/runlog-rollup/golden/evidence/
├── verify.log       # full passing verifier transcript
├── run.md           # image / version / digest metadata
└── adversarial.md   # benchmark-gaming attempts and the gates that reject them
```

The current golden run records:

- **20 / 20 visible tests passed**
- **12 / 12 held-out tests passed**
- **32 / 32 combined tests passed in one interpreter**
- **9 / 9 verifier gates passed**

## Repository Layout

```text
envs/
└── runlog-rollup/
    ├── repo/              # codebase visible to the agent
    ├── task.md            # task statement
    ├── heldout/           # hidden acceptance tests + integrity manifest
    ├── verify.sh          # scoring harness
    ├── golden/            # reference fix + evidence
    ├── Dockerfile
    └── requirements.txt
```

## Start Here

For the full environment contract, threat model, verifier logic, reproducibility details, and execution commands, see:

**[`envs/runlog-rollup/README.md`](envs/runlog-rollup/README.md)**

## Current Direction

The next step for this repository is expanding from a single environment into a broader suite of agentic coding tasks with varied defect classes, while preserving the same reproducibility and anti-gaming principles.
