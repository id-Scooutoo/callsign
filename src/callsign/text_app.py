"""Entrypoint for the text-triggered talking bot (interim mode; see text_bot.py).

No STT is loaded here — the bot only speaks, so startup skips whisper.
Run: python -m callsign.text_app
"""
from .brain import Brain, OpenAIBrain
from .config import Config
from .persona import load_persona
from .text_bot import TextBot


def build_brain(config: Config, persona: str):
    if config.backend in ("openai", "gemini"):
        return OpenAIBrain(
            config.openai_base_url, config.openai_api_key, config.llm_model, persona
        )
    return Brain(config.ollama_url, config.llm_model, persona)


def main() -> None:
    config = Config.from_env()
    persona = load_persona(config.persona_path)
    brain = build_brain(config, persona)
    tts = None
    if config.voice_enabled:
        from .tts import TTS  # heavy (torch/coqui) — only when voice is on

        tts = TTS(voiceprint_dir=config.voiceprint_dir)
    wr = None
    if config.wr_username and config.wr_password:
        from .whiterabbit import WhiteRabbit

        wr = WhiteRabbit(config.wr_base_url, config.wr_username, config.wr_password)
    bot = TextBot(config, brain, tts, wr=wr)
    print(
        f"backend={config.backend} model={config.llm_model} "
        f"voice={config.voice_enabled} whiterabbit={wr is not None} "
        f"code={bool(config.code_repo_path)}",
        flush=True,
    )
    print("warming up LLM...", "ok" if brain.warmup() else "failed", flush=True)
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
