# Golden verification evidence

Captured from GitHub Actions `Benchmark CI` run **31268446253** on 2026-08-08.

| Item | Value |
| --- | --- |
| Environment | `cursor-pagination` |
| Runner | Ubuntu 24.04 |
| Base image | `python@sha256:646fb0bca3dd3ea1bcc6feb72c17ed16eed6e10cffc732fcc1478bd3e7f02d7b` |
| Built task image | `sha256:2cabc63ee0e9ea78a4c95b3137de3bd0e3b56ebd42411050d50d55aa313b61ca` |
| Python | 3.12.13 |
| pytest | 9.1.1 |
| Visible tests | 13 / 13 passed |
| Held-out tests | 10 / 10 passed |
| Combined run | 23 / 23 passed |
| Verifier gates | 9 / 9 passed |
| Result | `PASS` |

## Verification command

```bash
golden/apply.sh /tmp/cursor-pagination-golden

docker run --rm --network none \
  --read-only --tmpfs /tmp:rw,exec,nosuid,size=256m \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --pids-limit 256 \
  -v /tmp/cursor-pagination-golden:/work/repo:ro \
  -v "$PWD/heldout:/verify/heldout:ro" \
  -v "$PWD/verify.sh:/verify/verify.sh:ro" \
  cursor-pagination:ci bash /verify/verify.sh
```

The exact verifier output from that successful matrix job is stored in
[`verify.log`](verify.log).
