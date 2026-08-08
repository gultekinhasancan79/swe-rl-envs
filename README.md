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

Scoring is based on **behaviour**, not similarity to a reference diff.

## Why This Matters

Coding-agent benchmarks are easy to make accidentally gameable. A candidate patch can appear correct by changing tests, exploiting collection configuration, hard-coding visible fixtures, branching on grader details, fixing only the visible symptom, or relying on environment drift.

These environments make those failure modes observable while keeping the evaluation boundary reproducible and auditable.

## Environments

| Environment | Defect class | Visible | Held-out | Gates |
| --- | --- | ---: | ---: | ---: |
| [`runlog-rollup`](envs/runlog-rollup) | Python process-lifetime state / shared mutable default | 20 | 12 | 9 |
| [`cursor-pagination`](envs/cursor-pagination) | Cursor protocol / premature termination on short pages | 13 | 10 | 9 |

### `runlog-rollup`

An internal record-rollup CLI leaks aggregation state between calls because a mutable default accumulator survives for the lifetime of the process. Held-out tests protect both sides of the public accumulator contract, and the strongest gate runs visible + hidden tests in one interpreter.

### `cursor-pagination`

A cursor-based API client incorrectly treats `len(items) < page_size` as terminal even when the backend returns a valid `next_cursor`. The environment tests protocol reasoning across short and empty intermediate pages, duplicate/order preservation, loop detection, and max-page safety.

The two tasks intentionally exercise different bug classes: **language/runtime state semantics** versus **distributed API contract semantics**.

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

Visible tests are not enough when a partial implementation can satisfy the reported symptom without restoring the real contract. Held-out suites use different data and exercise behaviours the candidate cannot solve by matching a single visible fixture.

### 2. Layered gates

No single integrity check is load-bearing. Plausible gaming attempts should trip multiple independent controls where possible.

### 3. Behaviour over diff similarity

The verifier does not require a candidate patch to resemble the golden patch. Any implementation satisfying the intended contract can pass.

### 4. Reproducible execution

Environments control important execution inputs:

- base images pinned by digest,
- direct and transitive test dependencies pinned by version and SHA-256,
- deterministic interpreter settings,
- no network during task execution or verification,
- controlled locale/timezone,
- normalized line endings,
- and fresh verification containers.

### 5. Explicit trust boundary

Candidate repositories are mounted read-only during scoring. Held-out tests and verifiers are supplied separately, making the scoring boundary explicit by construction.

## Verifier Gates

Both current environments use the same nine-layer verification shape:

| # | Gate | Purpose |
| ---: | --- | --- |
| 1 | Preflight | Reject a broken or incomplete harness |
| 2 | No network | Keep execution offline |
| 3 | Protected-file integrity | Reject modified/deleted visible tests and fixtures |
| 4 | No collection-time overrides | Detect added pytest/import hooks |
| 5 | Harness-awareness check | Detect source branching on grader details |
| 6 | Module provenance | Ensure imports resolve from the candidate repo |
| 7 | Visible suite | Validate the reported task behaviour |
| 8 | Held-out suite | Validate unseen parts of the contract |
| 9 | Combined process run | Validate visible + hidden behaviour together |

## Evidence

Each environment keeps its reference fix and evidence under `golden/`.

`runlog-rollup` currently records:

- **20 / 20 visible tests**
- **12 / 12 held-out tests**
- **32 / 32 combined tests**
- **9 / 9 verifier gates**

`cursor-pagination` is configured for:

- **13 visible tests**
- **10 held-out tests**
- **23 combined tests**
- **9 verifier gates**

The matrix `Benchmark CI` workflow builds and verifies each environment independently before changes can be merged.

## Repository Layout

```text
envs/
├── runlog-rollup/
│   ├── repo/
│   ├── task.md
│   ├── heldout/
│   ├── verify.sh
│   └── golden/
└── cursor-pagination/
    ├── repo/
    ├── task.md
    ├── heldout/
    ├── verify.sh
    └── golden/
```

## Start Here

- [`runlog-rollup` environment contract](envs/runlog-rollup/README.md)
- [`cursor-pagination` environment contract](envs/cursor-pagination/README.md)

## Contributing

New environments and verifier improvements should preserve the repository's standards around held-out behaviour, anti-gaming checks, reproducibility, and auditable golden evidence.

See **[`CONTRIBUTING.md`](CONTRIBUTING.md)** for the benchmark-authoring checklist and pull-request expectations.

## Current Direction

The next step is expanding the suite with additional defect classes while keeping the same reproducibility, trust-boundary, and anti-gaming standards across every environment.
