import discord

from .brain import Brain
from .config import Config
from .dialog_fsm import DialogFSM
from .discord_io import VoiceBot
from .persona import load_persona
from .stt import STT
from .tts import TTS
from .wake import contains_wake


def build_bot(config: Config) -> VoiceBot:
    persona = load_persona(config.persona_path)
    brain = Brain(config.ollama_url, config.llm_model, persona)
    stt = STT(model_size="large-v3")
    tts = TTS(voiceprint_dir=config.voiceprint_dir)
    fsm = DialogFSM(timeout=config.dialog_timeout)
    return VoiceBot(config, brain, stt, tts, fsm, contains_wake)


def main() -> None:
    config = Config.from_env()
    bot = build_bot(config)
    print("warming up LLM...", "ok" if bot.brain.warmup() else "failed (first turn slow)")

    @bot.event
    async def on_message(message: discord.Message):
        # "!join" in a text channel makes the bot join the author's voice channel
        if message.content.strip() == "!join" and message.author.voice:
            await bot.join(message.author.voice.channel)
            await message.channel.send(f'Wszedłem. Powiedz "{config.wake_word}".')

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
