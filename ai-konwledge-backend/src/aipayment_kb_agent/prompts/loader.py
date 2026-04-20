from __future__ import annotations

from pathlib import Path

import yaml


def load_yaml_prompt(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid yaml prompt file: {path}")
    return payload
