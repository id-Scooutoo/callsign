import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    discord_token: str
    backend: str
    ollama_url: str
    openai_base_url: str
    openai_api_key: str
    llm_model: str
    image_model: str
    wake_word: str
    dialog_timeout: float
    persona_path: str
    voiceprint_dir: str
    voice_enabled: bool
    wr_base_url: str
    wr_username: str
    wr_password: str
    code_repo_path: str

    @staticmethod
    def from_env() -> "Config":
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("missing env var: DISCORD_TOKEN")
        return Config(
            discord_token=token,
            backend=os.getenv("LLM_BACKEND", "ollama").lower(),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8317/v1"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "qwen3:8b"),
            image_model=os.getenv("IMAGE_MODEL", "gemini-3.1-flash-image"),
            wake_word=os.getenv("WAKE_WORD", "bot").lower(),
            dialog_timeout=float(os.getenv("DIALOG_TIMEOUT", "20")),
            persona_path=os.getenv("PERSONA_PATH", "persona.md"),
            voiceprint_dir=os.getenv("VOICEPRINT_DIR", "voiceprint"),
            voice_enabled=os.getenv("VOICE_ENABLED", "true").lower()
            not in ("0", "false", "no", "off"),
            wr_base_url=os.getenv("WR_BASE_URL", ""),
            wr_username=os.getenv("WR_USERNAME", ""),
            wr_password=os.getenv("WR_PASSWORD", ""),
            code_repo_path=os.getenv("CODE_REPO_PATH", ""),
        )
