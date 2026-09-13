# A visible-test pass can still be an incomplete fix

This walkthrough uses the existing `cursor-pagination` task to compare three
authored candidates against its unchanged verifier. It calls no model and is
not a new agent evaluation or an estimate of model success rates.

## Run it

Install Git, Python 3.10+ and Docker, with the Docker daemon running Linux
containers. Python on the host uses only its standard library; the task's
Python and test dependencies are installed in the pinned Docker image.

From a clone of this repository:

```bash
python examples/verification_walkthrough.py
```

Use `python3` on systems where Python has that name, or `py -3` on Windows.
No Bash installation is needed on the host for this helper. Windows uses
Docker Desktop in Linux-container mode. The workflow is also exercised on
Linux by GitHub Actions.

The first build may download the Docker base image and pinned packages.
Verification uses `--network none`, a read-only filesystem, separate read-only
candidate/held-out/verifier mounts, a temporary `/tmp`, dropped capabilities,
and the same memory and process limits as the existing CI verifier commands.

Each run creates a new output directory. To choose its location, pass a path
that does not already exist:

```bash
python examples/verification_walkthrough.py --output-dir artifacts/my-review
```

The helper builds from the current environment and then addresses the resulting
image by its immutable image ID for all three candidate runs.

## What changes between candidates?

The underlying task is a cursor API client. A server can return fewer items
than requested, or no items, and still provide a cursor for the next page.

| Candidate | Termination decision | Consequence |
| --- | --- | --- |
| `seeded` | Stop when `len(page.items) < page_size` | Drops later pages after a short response. |
| `partial` | Stop when `not page.items` | Handles non-empty short pages but still drops data after an empty intermediate page. |
| `reference` | Finish when `page.next_cursor is None` | Follows the cursor contract while preserving loop and page-count safeguards. |

The helper copies [`repo/`](../envs/cursor-pagination/repo) separately for each
candidate. The partial candidate receives
[`examples/partial-pagination.patch`](../examples/partial-pagination.patch);
the reference receives the existing
[`golden/fix.patch`](../envs/cursor-pagination/golden/fix.patch). The source
checkout, task, verifier, protected tests and historical golden evidence are
not edited by the walkthrough.

## Expected output

After image-build and candidate progress messages:

```text
Candidate   Visible  Held-out  Combined  Overall
seeded      FAIL     FAIL      FAIL      FAIL
partial     PASS     FAIL      FAIL      FAIL
reference   PASS     PASS      PASS      PASS

Walkthrough verified. Authored examples; no model was run.
```

All three candidates pass gates 1–6: setup, network isolation, protected-file
integrity, collection configuration, harness-awareness checks and module
provenance. Their behavioural results differ:

| Candidate | Visible passed | Held-out passed | Combined passed | Gates passed |
| --- | ---: | ---: | ---: | ---: |
| Seeded | 12/13 | 2/10 | 14/23 | 6/9 |
| Partial | 13/13 | 8/10 | 21/23 | 7/9 |
| Reference | 13/13 | 10/10 | 23/23 | 9/9 |

The partial candidate fails two held-out checks:

- `test_empty_intermediate_page_can_still_have_more_data`: a valid cursor after
  an empty page must still be followed.
- `test_short_page_does_not_hide_cursor_loop`: returning early must not hide a
  repeated cursor that should raise `PaginationError`.

The combined run repeats the visible and held-out suites in one interpreter;
it is not another independent set of 23 test cases. Gate counts describe this
walkthrough, not a fractional reward: the authoritative verifier returns
binary `PASS` or `FAIL`.

The helper itself exits **0 only if all three expected gate patterns occur**.
The seeded and partial verifier processes intentionally exit 1. A Docker error,
missing mount, protected-file mismatch, incomplete verifier run, or a different
gate pattern makes the helper fail; it is not accepted as a successful negative
control.

## Inspect the evidence

The output directory contains:

```text
build.log          image-build transcript
seeded.log         complete verifier output for the original defect
partial.log        complete verifier output for the incomplete fix
reference.log      complete verifier output for the reference solution
metadata.json      source commit, dirty-state flag, image ID, input hashes and results
candidates/        separate candidate repositories used in the checks
```

Candidate repositories include a local `.git` directory to keep patch
application relative to each copy. No commits are created in them. Generated
outputs under `artifacts/` are ignored by the source repository.

The **Reviewer walkthrough** CI job reruns this path and uploads logs and
metadata as `cursor-pagination-walkthrough`, retained for 30 days. Local
evidence stays in the chosen output directory. The older golden evidence under
the environment remains a separate record of its original measured revision.

## Scope

This demonstrates one deliberately incomplete fix rejected by the current
held-out tests. It does not establish that all incorrect fixes are rejected or
that all correct implementations are accepted. These are public authored tasks;
held-out material is kept out of the task container, but a reviewer with the
whole source repository can inspect it.

For an actual agent evaluation, give the agent only the task statement,
agent-visible repository and toolchain described in the
[environment contract](../envs/cursor-pagination/README.md#trust-boundary).
The other environment retains its separate
[`runlog-rollup` verification instructions](../envs/runlog-rollup/README.md#the-contract).
