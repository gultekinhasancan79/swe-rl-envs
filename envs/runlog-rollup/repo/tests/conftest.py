"""Shared fixtures for the runlog test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    """Directory holding the checked-in sample record files."""
    return FIXTURES


@pytest.fixture
def shard_a() -> Path:
    return FIXTURES / "shard_a.jsonl"


@pytest.fixture
def shard_b() -> Path:
    return FIXTURES / "shard_b.jsonl"
