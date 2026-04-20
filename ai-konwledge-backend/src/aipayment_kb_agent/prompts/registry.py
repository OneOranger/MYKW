from __future__ import annotations

from pathlib import Path

from aipayment_kb_agent.prompts.loader import load_yaml_prompt


class PromptRegistry:
    def __init__(self, prompts_root: Path):
        self.prompts_root = prompts_root

    def system_prompt(self, name: str) -> dict:
        path = self.prompts_root / "system" / f"{name}.yaml"
        return load_yaml_prompt(path)
