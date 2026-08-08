# syntax=docker/dockerfile:1
FROM python@sha256:646fb0bca3dd3ea1bcc6feb72c17ed16eed6e10cffc732fcc1478bd3e7f02d7b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PYTHONNOUSERSITE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=UTC \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

COPY requirements.txt /opt/requirements.txt
RUN pip install --no-deps --require-hashes --root-user-action=ignore \
        -r /opt/requirements.txt \
 && python -c "import pytest, pytest_timeout; print(pytest.__version__)"

RUN useradd --create-home --uid 1000 --shell /bin/bash agent

COPY --chown=agent:agent repo/ /work/repo/
ENV PYTHONPATH=/work/repo/src

WORKDIR /work/repo
USER agent

CMD ["python", "-m", "pytest"]
