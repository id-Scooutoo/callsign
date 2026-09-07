import numpy as np
from faster_whisper import WhisperModel


class STT:
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, pcm16k_mono: bytes, language: str = "pl") -> str:
        audio = np.frombuffer(pcm16k_mono, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(audio, language=language, beam_size=1)
        return " ".join(seg.text for seg in segments).strip()
