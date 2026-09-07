import os
import re
from pathlib import Path

import numpy as np
import parselmouth
import torch
from parselmouth.praat import call
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

MODEL_DIR = Path(
    os.path.expanduser(
        "~/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2"
    )
)

# Voice-tuning, chosen by A/B listening: XTTS renders this speaker at the right
# pitch (F0 ~= his real 110 Hz) but too bright, so darken formants slightly and
# leave pitch alone. formant_factor < 1 lowers the spectral envelope.
FORMANT_FACTOR = float(os.getenv("CS_FORMANT", "0.94"))
F0_FACTOR = float(os.getenv("CS_F0", "1.0"))


def _reshape(wav: np.ndarray, sr: int, formant_factor: float, f0_factor: float) -> np.ndarray:
    """Praat "Change gender" (PSOLA): lower the formants for a darker/bigger
    timbre, cleanly — no vocoder buzz (WORLD crackled over Discord's Opus).
    formant_factor < 1 lowers formants; pitch is kept (the clone already matches
    the real speaker's F0)."""
    if formant_factor == 1.0 and f0_factor == 1.0:
        return wav
    try:
        snd = parselmouth.Sound(
            np.ascontiguousarray(wav, dtype=np.float64), sampling_frequency=sr
        )
        # args: pitch_floor, pitch_ceiling, formant_shift_ratio,
        #       new_pitch_median (0 = keep), pitch_range_factor, duration_factor
        out = call(snd, "Change gender", 60, 500, formant_factor, 0.0, 1.0, 1.0)
        y = np.asarray(out.values, dtype=np.float32).flatten()
        peak = float(np.abs(y).max()) or 1.0
        return (y / peak * 0.97).astype(np.float32)
    except Exception:  # noqa: BLE001 - never let voice-shaping break a turn
        return wav


def _chunk_text(text: str, max_len: int = 200) -> list[str]:
    """Split into sentence-sized chunks so XTTS doesn't need spaCy and long
    replies aren't truncated. Splits on sentence enders, then commas, then hard
    length. Normalizes whitespace/newlines."""
    text = " ".join(text.split())
    chunks: list[str] = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_len:
            chunks.append(sentence)
            continue
        cur = ""
        for piece in re.split(r"(?<=,)\s+", sentence):
            if len(cur) + len(piece) + 1 <= max_len:
                cur = (cur + " " + piece).strip()
            else:
                if cur:
                    chunks.append(cur)
                cur = piece[:max_len]
        if cur:
            chunks.append(cur)
    return chunks


_INTENSE = re.compile(
    r"kurw|pierdol|jeb|chuj|zajeb|wkurw|debil|kretyn|idiot|hindus", re.IGNORECASE
)


def _emotion_params(text: str) -> tuple[float, float]:
    """Map a chunk's emotional intensity -> (temperature, speed): calm lines are
    flatter/slower, angry lines (CAPS, exclamations, swearing) more agitated."""
    letters = [c for c in text if c.isalpha()]
    caps_ratio = sum(c.isupper() for c in letters) / max(len(letters), 1)
    excl = text.count("!")
    swears = len(_INTENSE.findall(text))
    score = caps_ratio * 3.0 + min(excl, 4) * 0.18 + min(swears, 3) * 0.22
    temperature = min(0.9, 0.45 + score)   # calm ~0.45 -> agitated ~0.9
    speed = min(1.12, 1.0 + score * 0.15)  # angrier -> a touch faster
    return round(temperature, 3), round(speed, 3)


class TTS:
    SAMPLE_RATE = 24000

    def __init__(
        self,
        voiceprint_dir: str = "voiceprint",
        device: str = "cuda",
        formant_factor: float = FORMANT_FACTOR,
        f0_factor: float = F0_FACTOR,
    ):
        self.formant_factor = formant_factor
        self.f0_factor = f0_factor
        config = XttsConfig()
        config.load_json(str(MODEL_DIR / "config.json"))
        self.model = Xtts.init_from_config(config)
        self.model.load_checkpoint(config, checkpoint_dir=str(MODEL_DIR), eval=True)
        self.model.to(device)
        latents = torch.load(Path(voiceprint_dir) / "latents.pt", map_location=device)
        self.gpt_cond_latent = latents["gpt_cond_latent"]
        self.speaker_embedding = latents["speaker_embedding"]

    def speak(self, text: str, language: str = "pl") -> tuple[np.ndarray, int]:
        chunks = _chunk_text(text)
        if not chunks:
            return np.zeros(1, dtype=np.float32), self.SAMPLE_RATE
        parts = []
        for chunk in chunks:
            temperature, speed = _emotion_params(chunk)
            out = self.model.inference(
                chunk,
                language,
                self.gpt_cond_latent,
                self.speaker_embedding,
                temperature=temperature,
                length_penalty=1.0,
                repetition_penalty=2.0,
                top_k=50,
                top_p=0.8,
                speed=speed,
                enable_text_splitting=False,
            )
            parts.append(np.asarray(out["wav"], dtype=np.float32))
        wav = np.concatenate(parts) if len(parts) > 1 else parts[0]
        wav = _reshape(wav, self.SAMPLE_RATE, self.formant_factor, self.f0_factor)
        return wav, self.SAMPLE_RATE
