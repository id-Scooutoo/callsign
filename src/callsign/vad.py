SAMPLE_RATE = 16000
FRAME_MS = 20
FRAME_BYTES = int(SAMPLE_RATE * FRAME_MS / 1000) * 2  # 640


def _webrtc_predicate(aggressiveness: int):
    import webrtcvad

    vad = webrtcvad.Vad(aggressiveness)
    return lambda frame: vad.is_speech(frame, SAMPLE_RATE)


class Segmenter:
    """Feed 20 ms int16 mono @16k frames. Returns utterance bytes after silence."""

    def __init__(
        self,
        aggressiveness: int = 2,
        silence_ms: int = 600,
        min_speech_ms: int = 300,
        is_speech=None,
    ):
        self._is_speech = is_speech or _webrtc_predicate(aggressiveness)
        self._silence_frames = max(1, silence_ms // FRAME_MS)
        self._min_speech_frames = max(1, min_speech_ms // FRAME_MS)
        self._reset()

    def _reset(self) -> None:
        self._buf = bytearray()
        self._speech_count = 0
        self._silence_run = 0
        self._in_speech = False

    def push(self, frame: bytes) -> bytes | None:
        if len(frame) != FRAME_BYTES:
            raise ValueError(f"frame must be {FRAME_BYTES} bytes, got {len(frame)}")
        if self._is_speech(frame):
            self._in_speech = True
            self._silence_run = 0
            self._speech_count += 1
            self._buf.extend(frame)
            return None
        if self._in_speech:
            self._silence_run += 1
            self._buf.extend(frame)
            if self._silence_run >= self._silence_frames:
                out = (
                    bytes(self._buf)
                    if self._speech_count >= self._min_speech_frames
                    else None
                )
                self._reset()
                return out
        return None
