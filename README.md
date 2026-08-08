# swe-rl-envs

Reproducible evaluation environments for agentic coding benchmarks.

Each environment ships a small codebase with a seeded defect, a task statement
written for an agent, a held-out test suite the agent never sees, and a
verifier that scores a candidate patch behind a series of gates. An
environment is only useful if it does two things: reject the seeded defect,
and accept any genuinely correct fix. Both are demonstrated per environment
under `golden/evidence/`.

## Environments

| Environment | Defect | Gates |
| --- | --- | --- |
| [`runlog-rollup`](envs/runlog-rollup) | Shared mutable default accumulator leaks state across calls | 9 |

## Design notes

- **Held-out tests.** A partial fix can pass every visible test while leaving
  the defect in place for other callers. Nothing a checksum or a file listing
  can see catches that — only a behavioural test the candidate could not read.
- **Layered gates.** Most gaming attempts trip more than one gate, so a gap in
  any single check does not silently become a pass.
- **Behaviour, not diffs.** Grading is on the contract the code must satisfy,
  not on resemblance to the reference patch.
- **Pinned by digest.** Base image and dependencies are pinned by hash, so a
  run today and a run in six months score identically — and everything outside
  the mounted repo is trusted by construction rather than by checking.

See [`envs/runlog-rollup/README.md`](envs/runlog-rollup/README.md) for the
environment contract and how to run the verifier.