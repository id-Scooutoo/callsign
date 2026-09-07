import numpy as np

from callsign.audio import (
    float_to_int16,
    mono_to_stereo,
    resample_int16,
    stereo_to_mono,
)


def test_stereo_to_mono_averages():
    stereo = np.array([100, 200, 300, 400], dtype=np.int16).tobytes()  # L,R,L,R
    mono = np.frombuffer(stereo_to_mono(stereo), dtype=np.int16)
    assert list(mono) == [150, 350]


def test_resample_changes_length_proportionally():
    src = (np.zeros(48000, dtype=np.int16)).tobytes()  # 1 s @48k mono
    out = np.frombuffer(resample_int16(src, 48000, 16000), dtype=np.int16)
    assert abs(len(out) - 16000) <= 2


def test_float_to_int16_clips():
    f = np.array([0.0, 1.5, -1.5], dtype=np.float32)
    out = np.frombuffer(float_to_int16(f), dtype=np.int16)
    assert out[0] == 0 and out[1] == 32767 and out[2] == -32767


def test_mono_to_stereo_duplicates():
    mono = np.array([10, 20], dtype=np.int16).tobytes()
    st = np.frombuffer(mono_to_stereo(mono), dtype=np.int16)
    assert list(st) == [10, 10, 20, 20]
