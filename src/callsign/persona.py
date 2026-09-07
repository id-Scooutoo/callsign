from pathlib import Path


def load_persona(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def build_messages(
    persona: str, history: list[tuple[str, str]], user_text: str
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": persona}]
    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})
    messages.append({"role": "user", "content": user_text})
    return messages
