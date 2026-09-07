import os
import sys
from pathlib import Path

import soundfile as sf
import soxr
import torch
import TTS.tts.models.xtts as _xtts_mod
from TTS.api import TTS as HighLevelTTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts


def _load_audio_sf(audiopath, sampling_rate):
    """Avoid torchaudio->torchcodec (needs libnvrtc.so.13 / CUDA 13; torch is
    cu128 / CUDA 12.8). Load via soundfile+soxr; return (1, N) float in [-1, 1].
    """
    a, lsr = sf.read(str(audiopath), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    if lsr != sampling_rate:
        a = soxr.resample(a, lsr, sampling_rate)
    t = torch.tensor(a, dtype=torch.float32).unsqueeze(0)
    t.clip_(-1, 1)
    return t


_xtts_mod.load_audio = _load_audio_sf

MODEL_ID = "tts_models/multilingual/multi-dataset/xtts_v2"
MODEL_DIR = Path(
    os.path.expanduser(
        "~/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2"
    )
)


def main(clips_dir: str, out_dir: str) -> None:
    clips = sorted(str(p) for p in Path(clips_dir).glob("*.wav"))
    assert clips, f"no wav clips in {clips_dir}"
    HighLevelTTS(MODEL_ID)  # triggers one-time download of the model files
    config = XttsConfig()
    config.load_json(str(MODEL_DIR / "config.json"))
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir=str(MODEL_DIR), eval=True)
    model.cuda()
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
        audio_path=clips
    )
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    torch.save(
        {"gpt_cond_latent": gpt_cond_latent, "speaker_embedding": speaker_embedding},
        Path(out_dir) / "latents.pt",
    )
    print("saved", Path(out_dir) / "latents.pt")


if __name__ == "__main__":
    main(
        sys.argv[1] if len(sys.argv) > 1 else "voiceprint/clips",
        sys.argv[2] if len(sys.argv) > 2 else "voiceprint",
    )
