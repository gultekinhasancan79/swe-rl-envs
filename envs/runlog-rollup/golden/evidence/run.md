# Evidence: reference solution passes verify.sh

Captured 2026-08-05T19:03:03Z on 29.2.1 (linux/amd64).

| Item | Value |
| ---- | ----- |
| Base image | `python@sha256:646fb0bca3dd3ea1bcc6feb72c17ed16eed6e10cffc732fcc1478bd3e7f02d7b` |
| Task image ID | `sha256:1a1a738a7c9c9b74d37c198506449f9133a0bc024b9c480976276dbccbb03eb6` |
| Interpreter | Python 3.12.13 |
| pytest | pytest 9.1.1 |
| fix.patch sha256 | `e3d08cbebee269e95302fcb5523da3a10966de647a614d17ac975fe9b8240ab8` |
| Exit code | 0 (`RESULT: PASS`) |
| Gates passed | 9/9 — 20 visible, 12 held-out, 32 combined |

## Command

```sh
golden/apply.sh /tmp/golden-candidate

docker run --rm --network none \
  --read-only --tmpfs /tmp:rw,exec,nosuid,size=256m \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --pids-limit 256 \
  -v /tmp/golden-candidate:/work/repo:ro \
  -v "$PWD/heldout:/verify/heldout:ro" \
  -v "$PWD/verify.sh:/verify/verify.sh:ro" \
  runlog-rollup:1 bash /verify/verify.sh
```

Full output in `verify.log`. For contrast, the same command against the
unpatched `repo/` exits 1 with the visible and held-out gates both failing.
