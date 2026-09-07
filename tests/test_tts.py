from pathlib import Path

import numpy as np
import pytest

from callsign.tts import TTS


@pytest.mark.gpu
def test_speak_returns_audio():
    if not Path("voiceprint/latents.pt").exists():
        pytest.skip("run scripts/prep_voice.py first")
    tts = TTS(voiceprint_dir="voiceprint")
    wav, sr = tts.speak("Cześć, słyszysz mnie?")
    assert sr == 24000
    assert isinstance(wav, np.ndarray) and wav.size > sr  # >1 s of audio
    assert float(np.abs(wav).max()) > 0.01                # not silence
