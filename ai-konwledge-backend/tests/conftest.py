from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def set_test_env(tmp_path: Path):
    os.environ["OPENAI_ENABLED"] = "false"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["LOG_DIR"] = str(tmp_path / "logs")
    yield
