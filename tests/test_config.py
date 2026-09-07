import pytest

from callsign.config import Config


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "tok")
    monkeypatch.setenv("LLM_MODEL", "qwen3:8b")
    monkeypatch.setenv("DIALOG_TIMEOUT", "15")
    cfg = Config.from_env()
    assert cfg.discord_token == "tok"
    assert cfg.llm_model == "qwen3:8b"
    assert cfg.dialog_timeout == 15.0
    assert cfg.wake_word == "bot"  # default, lowercased


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(ValueError):
        Config.from_env()
