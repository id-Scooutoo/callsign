"""Image generation via the OpenAI-compatible proxy (Gemini image model,
"nano banana"). The image model returns the picture inline in a chat
completion under message.images[].image_url.url as a base64 data URI."""
import base64

import requests


def generate(base_url: str, api_key: str, model: str, prompt: str,
             timeout: float = 120.0) -> bytes | None:
    """Return image bytes (jpeg/png) for the prompt, or None on failure."""
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        images = resp.json()["choices"][0]["message"].get("images") or []
        if not images:
            return None
        url = images[0]["image_url"]["url"]  # data:image/...;base64,....
        b64 = url.split(",", 1)[1]
        return base64.b64decode(b64)
    except Exception:  # noqa: BLE001 - never crash a turn on image failure
        return None
