## What changes?

Describe the environment, verifier, reproducibility, documentation, or evidence change.

## Measurement impact

What benchmark property changes? If scoring semantics do not change, say so explicitly.

## Validation

- [ ] Seeded/broken state is still rejected
- [ ] Golden/correct state is accepted
- [ ] Visible tests behave as intended
- [ ] Held-out tests exercise the intended contract
- [ ] Combined/same-process behaviour is covered where relevant
- [ ] Verifier integrity checks still protect the scoring boundary
- [ ] Network/reproducibility assumptions are unchanged or documented
- [ ] Dependency/image/checksum/test-count changes are documented
- [ ] Golden evidence has been regenerated when required
- [ ] CI passes

## Adversarial checks

List partial fixes, test tampering, harness-aware implementations, or other plausible gaming attempts you tried and how the verifier responds.

## Reviewer notes

Call out anything that deserves special attention, especially changes to protected files, held-out material, verifier semantics, hashes/digests, or the trust boundary.
