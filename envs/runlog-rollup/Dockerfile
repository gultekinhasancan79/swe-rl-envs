# syntax=docker/dockerfile:1
#
# Image for the runlog-rollup evaluation environment.
#
# Pinned by digest, not by tag: `python:3.12-slim` is a moving target that is
# rebuilt whenever Debian ships a security update, so a tag pin would silently
# change the interpreter patch level and the OpenSSL underneath it between the
# day the task was authored and the day a run is scored.
#
#   python:3.12-slim @ 2026-08-05
FROM python@sha256:646fb0bca3dd3ea1bcc6feb72c17ed16eed6e10cffc732fcc1478bd3e7f02d7b

# Deterministic interpreter behaviour:
#   PYTHONDONTWRITEBYTECODE - no .pyc files, so a read-only repo mount works
#                             and stale bytecode can never mask a source change
#   PYTHONHASHSEED          - stable set/dict iteration in any incidental spot
#   PYTHONNOUSERSITE        - ~/.local can never shadow the pinned toolchain
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PYTHONNOUSERSITE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=UTC \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# This is the only step that needs the network, and it happens at build time.
# Task execution and verification both run with `--network none`.
COPY requirements.txt /opt/requirements.txt
RUN pip install --no-deps --require-hashes --root-user-action=ignore \
        -r /opt/requirements.txt \
 && python -c "import pytest, pytest_timeout; print(pytest.__version__)"

# Unprivileged user. The agent never needs root, and running as root would let a
# candidate solution rewrite the interpreter or the installed toolchain.
RUN useradd --create-home --uid 1000 --shell /bin/bash agent

# The project under test. The held-out tests and verify.sh are deliberately NOT
# copied in -- they are bind-mounted at verification time only.
COPY --chown=agent:agent repo/ /work/repo/

# `src` on the path instead of `pip install -e .`: it keeps the build free of a
# build backend, and it means verification does not depend on install state that
# a candidate solution could have mutated.
ENV PYTHONPATH=/work/repo/src

WORKDIR /work/repo
USER agent

CMD ["python", "-m", "pytest"]
