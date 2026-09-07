import numpy as np
import soxr


def stereo_to_mono(pcm_s16_stereo: bytes) -> bytes:
    a = np.frombuffer(pcm_s16_stereo, dtype=np.int16).astype(np.int32)
    a = a.reshape(-1, 2)
    mono = ((a[:, 0] + a[:, 1]) // 2).astype(np.int16)
    return mono.tobytes()


def float_to_int16(f: np.ndarray) -> bytes:
    clipped = np.clip(f, -1.0, 1.0)
    return (clipped * 32767.0).round().astype(np.int16).tobytes()


def resample_int16(pcm_s16_mono: bytes, src_rate: int, dst_rate: int) -> bytes:
    a = np.frombuffer(pcm_s16_mono, dtype=np.int16).astype(np.float32) / 32768.0
    out = soxr.resample(a, src_rate, dst_rate)
    return float_to_int16(out)


def mono_to_stereo(pcm_s16_mono: bytes) -> bytes:
    a = np.frombuffer(pcm_s16_mono, dtype=np.int16)
    return np.repeat(a, 2).tobytes()
