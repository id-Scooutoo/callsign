# callsign

A Discord bot that wakes when you call it by name, holds a short spoken
conversation through a local LLM, and answers in a voice you supply. Speech
recognition, the language model and speech synthesis all run on your own
machine — nothing about a conversation leaves it.

The name, the voice and the personality are all configuration. Nothing about
this bot is hardcoded to any particular person.

```
you speak ──▶ VAD ──▶ wake word? ──▶ STT ──▶ LLM (+persona) ──▶ TTS ──▶ bot speaks
                          │                                        │
                    silent if not          your voiceprint ────────┘
                    addressed                (XTTS-v2 latents)
```

After a reply the bot stays awake for `DIALOG_TIMEOUT` seconds, so a
back-and-forth does not need the wake word every turn. Go quiet and it sleeps.

## Why the wake word is not a substring match

Polish inflects names. Someone saying *"Marku, słyszysz?"* is addressing a bot
called **marek**, and a bot that only matches its nominative form misses half
of what is said to it. Matching a stem plus a wildcard is worse: it wakes on
*"marketing"*.

`callsign.wake` picks a small set of real case endings from the shape of the
name — `-ek` names drop the `e` from the stem, `-a` names take a different set,
consonant endings take a third — and matches those exact forms on word
boundaries. Names that are not Polish personal names fall back to an exact
match, so `jarvis` or `r2d2` work too.

## Requirements

- Linux, or WSL2 on Windows. Python 3.11+ (tested on 3.13)
- An NVIDIA GPU for voice mode. RTX 50-series (Blackwell) needs a **cu128**
  torch build — see the install order below
- [Ollama](https://ollama.com) with a model pulled (`qwen3:8b` by default), or
  any OpenAI-compatible endpoint

Text-only mode drops the GPU requirement entirely — see *Text mode*.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel

# PyTorch FIRST, from the cu128 index. A later dependency can silently
# downgrade torch, so install it before anything else and re-check after.
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128

pip install -r requirements.txt
pip install -e .

python scripts/gpu_smoke.py   # prints your compute capability, e.g. sm_120
cp .env.example .env          # then fill in DISCORD_TOKEN and WAKE_WORD
```

### Discord app

1. Discord Developer Portal → New Application → Bot → copy the **token** into `.env`.
2. Enable **Message Content Intent** and **Server Members Intent** under
   Bot → Privileged Intents.
3. OAuth2 URL Generator: scope `bot`; permissions Connect, Speak, View Channels,
   Read Message History. Open the generated URL and invite the bot.

### Ollama reachable from WSL

```bash
curl -s http://127.0.0.1:11434/api/tags | head -c 200
```

Connection refused usually means WSL networking is not mirrored. Either set
`networkingMode=mirrored` in `.wslconfig`, or point `OLLAMA_URL` at the host IP.

### Give it a voice

See [`voiceprint/README.md`](voiceprint/README.md) for how to build a
voiceprint from a recording, and **[`VOICE-CONSENT.md`](VOICE-CONSENT.md)
before you use anyone's voice but your own**.

```bash
COQUI_TOS_AGREED=1 python scripts/make_voiceprint.py
```

Skip this and set `VOICE_ENABLED=false` to run without synthesis.

### Give it a personality

```bash
cp persona.example.md persona.md
```

Then rewrite it. It becomes the system prompt, so it decides how the bot
answers — the example is deliberately plain.

## Run

```bash
source .venv/bin/activate
python -m callsign.app
```

Then, in Discord: join a voice channel, type `!join` in a text channel, and say
your wake word. The bot wakes silently; ask a question and it answers aloud
within a couple of seconds.

### Text mode

`python -m callsign.text_app` runs the same brain with no audio at all — no GPU,
no voiceprint, no voice channel. It answers messages in text. This is what
[`deploy/DEPLOY.md`](deploy/DEPLOY.md) puts on a cheap CPU VPS for 24/7 uptime.

## Configuration

Everything lives in `.env`; see `.env.example` for the full list.

| Variable | Default | |
|---|---|---|
| `DISCORD_TOKEN` | — | required |
| `WAKE_WORD` | `bot` | what you call it |
| `PERSONA_PATH` | `persona.md` | system prompt file |
| `LLM_BACKEND` | `ollama` | `ollama`, or `openai` for any OpenAI-compatible endpoint |
| `LLM_MODEL` | `qwen3:8b` | model name for the chosen backend |
| `DIALOG_TIMEOUT` | `20` | seconds it stays awake after a reply |
| `VOICE_ENABLED` | `true` | `false` runs text-only |
| `VOICEPRINT_DIR` | `voiceprint` | where the speaker latents live |

Optional integrations, off unless configured: `CODE_REPO_PATH` lets the bot
grep a local checkout to answer "which module handles X"; `WR_BASE_URL` /
`WR_USERNAME` / `WR_PASSWORD` connect a project tracker. Both are examples of
plugging your own tools in, not requirements.

## Tests

```bash
PYTHONPATH=src pytest -m "not gpu"   # pure logic, no GPU or models needed
PYTHONPATH=src pytest -m gpu         # STT/TTS, needs GPU + models + a voiceprint
```

## Notes from the build

- The voice scripts patch XTTS's audio loader to use `soundfile` instead of
  `torchaudio`. torchcodec 0.15 (torchaudio's default backend) links CUDA 13
  libraries while torch here is cu128, so `torchaudio.load` crashes on
  `libnvrtc.so.13`.
- `coqui-tts` XTTS-v2 imports a symbol removed in transformers 5.x — the pin in
  `requirements.txt` is deliberate.
- `webrtcvad` does not build on Python 3.13; `webrtcvad-wheels` is the same
  module with wheels that do.
- discord.py's voice support uses `audioop`, removed from the stdlib in 3.13,
  hence `audioop-lts`.

## License

MIT.
