# Golden verification evidence

This directory records the reference solution for the `cursor-pagination`
environment.

The authoritative verification path is:

```bash
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

Expected acceptance criteria:

- 13 / 13 visible tests,
- 10 / 10 held-out tests,
- 23 / 23 tests in the combined interpreter run,
- all 9 verifier gates,
- `RESULT: PASS`.

GitHub Actions runs this same isolated golden verification path before the
environment is merged. A captured passing transcript is stored in
`verify.log`.
