from __future__ import annotations


def compress_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    tail = messages[-max_items:]
    lines = [f"{msg['role']}: {msg['content']}" for msg in tail]
    return "\n".join(lines)
