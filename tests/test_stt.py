import wave

import pytest

from callsign.stt import STT


def read_pcm16(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        return w.readframes(w.getnframes())


@pytest.mark.gpu
def test_transcribes_polish_digits():
    stt = STT(model_size="large-v3")
    text = stt.transcribe(read_pcm16("tests/data/pl_sample.wav")).lower()
    assert "trzy" in text or "3" in text
