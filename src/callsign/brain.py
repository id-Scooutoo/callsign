import re

import requests

from .persona import build_messages

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_think(text: str) -> str:
    return _THINK.sub("", text).strip()


def _tidy(text: str) -> str:
    """Trim a trailing incomplete sentence left by the token cap.

    Leaves code blocks alone (chopping them would break the code)."""
    text = text.strip()
    if "```" in text:
        return text
    if text and text[-1] not in ".!?…":
        cut = max(text.rfind(c) for c in ".!?…")
        if cut > 0:
            text = text[: cut + 1]
    return text.strip()


class Brain:
    def __init__(
        self,
        url: str,
        model: str,
        persona: str,
        max_history: int = 6,
        keep_alive: str = "30m",
        num_predict: int = 512,
    ):
        self.url = url.rstrip("/")
        self.model = model
        self.persona = persona
        self.max_history = max_history
        self.keep_alive = keep_alive
        self.num_predict = num_predict
        self.history: list[tuple[str, str]] = []

    def reply(self, user_text: str, context: str = "", timeout: float = 60.0) -> str:
        messages = build_messages(
            self.persona, self.history[-self.max_history:], user_text
        )
        if context:
            messages.insert(
                len(messages) - 1,
                {
                    "role": "system",
                    "content": "Świeże informacje z sieci "
                    "(użyj ich, odpowiedz w charakterze):\n" + context,
                },
            )
        resp = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "keep_alive": self.keep_alive,
                "options": {"temperature": 0.8, "num_predict": self.num_predict},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        text = _tidy(strip_think(resp.json()["message"]["content"]))
        self.history.append((user_text, text))
        return text

    def warmup(self, timeout: float = 240.0) -> bool:
        """Preload the model into VRAM so the first real turn is fast.

        Best-effort: returns True on success, False on any failure (the bot
        still works, the first turn is just slower).
        """
        try:
            resp = requests.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ok"}],
                    "stream": False,
                    "think": False,
                    "keep_alive": self.keep_alive,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            return True
        except Exception:
            return False


class OpenAIBrain:
    """OpenAI-compatible chat backend (e.g. the local cli-proxy-api that serves
    Gemini). Same interface as Brain."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        persona: str,
        max_history: int = 6,
        num_predict: int = 512,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.persona = persona
        self.max_history = max_history
        self.num_predict = num_predict
        self.history: list[tuple[str, str]] = []

    def reply(self, user_text: str, context: str = "", timeout: float = 90.0) -> str:
        messages = build_messages(
            self.persona, self.history[-self.max_history:], user_text
        )
        if context:
            messages.insert(
                len(messages) - 1,
                {
                    "role": "system",
                    "content": "Świeże informacje z sieci "
                    "(użyj ich, odpowiedz w charakterze):\n" + context,
                },
            )
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "temperature": 0.9,
                "max_tokens": self.num_predict,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        text = _tidy(strip_think(content))
        self.history.append((user_text, text))
        return text

    def warmup(self, timeout: float = 60.0) -> bool:
        try:
            requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ok"}],
                    "stream": False,
                    "max_tokens": 4,
                },
                timeout=timeout,
            ).raise_for_status()
            return True
        except Exception:
            return False
