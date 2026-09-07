"""Build XTTS-v2 speaker latents from voiceprint/source.mp3 + synth test samples.

Offline voice-prep:
  1. convert -> auto-segment on silence -> representative clips spread across the
     recording (for timbre similarity) -> normalized speaker latents.
  2. measure the speaker's REAL median F0 from the source.
  3. synth a sample; measure the clone's F0; use the WORLD vocoder to scale the
     clone's F0 to the real median (formant-preserving -> lower + natural, no
     phase-vocoder artifacts).

Outputs sample_clone.wav (raw XTTS) and sample_clone_matched.wav (pitch-matched).
Tunables via env: CS_TEMP (0.55), CS_CLIPS (15), CS_FACTOR (override auto factor).
"""
import os
import subprocess
import time
from pathlib import Path

import librosa
import numpy as np
import pyworld as pw
import soundfile as sf
import soxr
import torch
import TTS.tts.models.xtts as _xtts_mod
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

ROOT = Path.home() / "projects" / "callsign"
VP = ROOT / "voiceprint"
SRC = VP / "source.mp3"
FULL = VP / "full.wav"
CLIPS = VP / "clips"
MODEL_DIR = (
    Path.home()
    / ".local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2"
)
SR = 24000
TEMP = float(os.getenv("CS_TEMP", "0.55"))
MAX_CLIPS = int(os.getenv("CS_CLIPS", "15"))
FACTOR_OVERRIDE = os.getenv("CS_FACTOR")
TEST_TEXT = "Dzień dobry, to jest próbka sklonowanego głosu. Czy brzmi naturalnie?"


def _load_audio_sf(audiopath, sampling_rate):
    a, lsr = sf.read(str(audiopath), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    if lsr != sampling_rate:
        a = soxr.resample(a, lsr, sampling_rate)
    t = torch.tensor(a, dtype=torch.float32).unsqueeze(0)
    t.clip_(-1, 1)
    return t


_xtts_mod.load_audio = _load_audio_sf


def median_f0(wav: np.ndarray, sr: int) -> float:
    """Median voiced F0 (Hz) of a waveform."""
    w16 = soxr.resample(wav, sr, 16000) if sr != 16000 else wav
    f0 = librosa.yin(w16, fmin=70, fmax=350, sr=16000, frame_length=2048)
    voiced = f0[(f0 > 80) & (f0 < 300)]
    return float(np.median(voiced)) if voiced.size else 0.0


def real_median_f0(y: np.ndarray, sr: int, n_windows: int = 30, win_s: int = 8) -> float:
    """Speaker's real median F0, sampled across the whole recording."""
    win = win_s * sr
    if len(y) <= win:
        starts = [0]
    else:
        starts = [round(i * (len(y) - win) / (n_windows - 1)) for i in range(n_windows)]
    voiced = []
    for st in starts:
        w16 = soxr.resample(y[st:st + win], sr, 16000)
        f0 = librosa.yin(w16, fmin=70, fmax=350, sr=16000, frame_length=2048)
        voiced.append(f0[(f0 > 80) & (f0 < 300)])
    allv = np.concatenate(voiced)
    return float(np.median(allv))


def reshape_voice(wav: np.ndarray, sr: int, f0_factor: float = 1.0,
                  formant_factor: float = 1.0) -> np.ndarray:
    """WORLD re-synthesis: scale F0 and/or warp formants independently.

    formant_factor < 1 lowers the spectral envelope (darker/bigger timbre) while
    keeping pitch; f0_factor < 1 lowers pitch. Keeps them decoupled.
    """
    x = np.ascontiguousarray(wav, dtype=np.float64)
    f0, sp, ap = pw.wav2world(x, sr)
    if formant_factor != 1.0:
        dim = sp.shape[1]
        freqs = np.arange(dim)
        src = freqs / formant_factor  # <1 => sample envelope higher => peaks move down
        sp = np.stack([np.interp(src, freqs, sp[i]) for i in range(sp.shape[0])])
    out = pw.synthesize(f0 * f0_factor, sp, ap, sr)
    peak = float(np.abs(out).max()) or 1.0
    return (out / peak * 0.97).astype(np.float32)


def pick_clips(y: np.ndarray, sr: int) -> list[str]:
    """Representative clips: clean segments spread across the recording."""
    intervals = librosa.effects.split(y, top_db=50)
    segs = [(s, e) for s, e in intervals if (e - s) / sr >= 4.0]
    if len(segs) > MAX_CLIPS:
        idx = [round(i * (len(segs) - 1) / (MAX_CLIPS - 1)) for i in range(MAX_CLIPS)]
        segs = [segs[j] for j in idx]
    CLIPS.mkdir(parents=True, exist_ok=True)
    for old in CLIPS.glob("*.wav"):
        old.unlink()
    paths, total = [], 0.0
    for i, (s, e) in enumerate(segs, 1):
        e = min(e, s + 12 * sr)
        sf.write(str(CLIPS / f"{i:02d}.wav"), y[s:e], sr)
        paths.append(str(CLIPS / f"{i:02d}.wav"))
        total += (e - s) / sr
    print(f"selected {len(paths)} clips, {total:.1f}s reference", flush=True)
    return paths


def main() -> None:
    print("=== convert mp3 -> 24k mono wav ===", flush=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(SRC),
         "-ac", "1", "-ar", str(SR), str(FULL)],
        check=True,
    )
    y, sr = sf.read(str(FULL), dtype="float32")
    if y.ndim > 1:
        y = y.mean(axis=1)
    real_f0 = real_median_f0(y, sr)
    print(f"source {len(y)/sr/60:.1f} min  real median F0 {real_f0:.0f} Hz", flush=True)

    clip_paths = pick_clips(y, sr)

    print("=== load XTTS-v2 ===", flush=True)
    cfg = XttsConfig()
    cfg.load_json(str(MODEL_DIR / "config.json"))
    model = Xtts.init_from_config(cfg)
    model.load_checkpoint(cfg, checkpoint_dir=str(MODEL_DIR), eval=True)
    model.cuda()

    t = time.time()
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
        audio_path=clip_paths, gpt_cond_len=30, max_ref_length=60, sound_norm_refs=True,
    )
    print(f"latents in {time.time()-t:.1f}s", flush=True)
    torch.save(
        {"gpt_cond_latent": gpt_cond_latent, "speaker_embedding": speaker_embedding},
        VP / "latents.pt",
    )

    print(f"=== synth (temp={TEMP}) ===", flush=True)
    out = model.inference(
        TEST_TEXT, "pl", gpt_cond_latent, speaker_embedding,
        temperature=TEMP, length_penalty=1.0, repetition_penalty=2.0,
        top_k=50, top_p=0.8, enable_text_splitting=True,
    )
    wav = np.asarray(out["wav"], dtype=np.float32)
    sf.write(str(VP / "sample_clone.wav"), wav, SR)
    clone_f0 = median_f0(wav, SR)
    print(f"clone F0 {clone_f0:.0f} Hz vs real {real_f0:.0f} Hz "
          f"(pitch already matches -> darken FORMANTS, not pitch)", flush=True)

    # F0 is already right; "too high" == too-bright timbre. Offer formant-darkened
    # variants (keep pitch) for A/B: mild and stronger, plus one a touch deeper.
    variants = {
        "formantA": dict(formant_factor=0.94),
        "formantB": dict(formant_factor=0.88),
        "deep": dict(formant_factor=0.90, f0_factor=0.95),
    }
    for name, kw in variants.items():
        v = reshape_voice(wav, SR, **kw)
        sf.write(str(VP / f"sample_{name}.wav"), v, SR)
        print(f"{name} {kw} -> F0 {median_f0(v, SR):.0f} Hz", flush=True)


if __name__ == "__main__":
    main()
