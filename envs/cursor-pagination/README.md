# cursor-pagination — agentic coding evaluation environment

A self-contained coding-agent task built around a cursor-pagination contract
bug: the client incorrectly treats a short page as terminal even when the
backend provides a `next_cursor`.

This environment complements `runlog-rollup` with a different defect class:
**protocol/contract reasoning across page boundaries** rather than Python
process-lifetime state.

## Benchmark shape

| Component | Count / behavior |
| --- | --- |
| Visible tests | 13 |
| Held-out tests | 10 |
| Combined tests | 23 |
| Verifier gates | 9 |
| Network during task / verification | none |
| Scoring | behaviour-based pass/fail |

## Trust boundary

```text
repo/           agent-visible code and visible tests
task.md         agent-visible task statement
heldout/        hidden acceptance tests + protected-file manifest
verify.sh       scorer, supplied only at verification time
golden/         reference fix and auditable evidence
```

Only `repo/` and the pinned test toolchain enter the task image. Held-out tests
and the verifier are bind-mounted read-only into a fresh container for scoring.

## The seeded defect

`collect_all` currently assumes:

```text
len(page.items) < page_size  =>  pagination is finished
```

That assumption is invalid for cursor APIs whose backend may filter or shard
results after page construction. The authoritative termination signal is the
cursor contract, not page fullness.

The visible suite contains one direct regression for the reported symptom.
Held-out tests expand the contract to empty intermediate pages, multiple short
pages, duplicate preservation, unusual but valid cursors, generated runtime
values, loop detection, and max-page safety.

## Nine verifier gates

1. preflight,
2. no network,
3. protected visible files unchanged,
4. no collection-time overrides,
5. source unaware of grader/test internals,
6. module provenance,
7. visible suite,
8. held-out suite,
9. visible + held-out suites in one interpreter.

## Run the golden verification

```bash
docker build -t cursor-pagination:1 .
golden/apply.sh /tmp/cursor-pagination-golden

docker run --rm --network none \
  --read-only --tmpfs /tmp:rw,exec,nosuid,size=256m \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --pids-limit 256 \
  -v /tmp/cursor-pagination-golden:/work/repo:ro \
  -v "$PWD/heldout:/verify/heldout:ro" \
  -v "$PWD/verify.sh:/verify/verify.sh:ro" \
  cursor-pagination:1 bash /verify/verify.sh
```

The verifier prints `RESULT: PASS` only when every gate succeeds.
