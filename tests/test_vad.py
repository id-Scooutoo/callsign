from callsign.vad import FRAME_BYTES, Segmenter


def speech_frame():   # marker byte 1 => speech
    return b"\x01" + b"\x00" * (FRAME_BYTES - 1)


def silence_frame():  # marker byte 0 => silence
    return b"\x00" * FRAME_BYTES


def marker_is_speech(frame: bytes) -> bool:
    return frame[0] == 1


def test_emits_utterance_after_trailing_silence():
    seg = Segmenter(silence_ms=60, min_speech_ms=40, is_speech=marker_is_speech)
    for _ in range(5):                       # 100 ms speech
        assert seg.push(speech_frame()) is None
    for _ in range(2):                       # 40 ms silence — not enough
        assert seg.push(silence_frame()) is None
    out = seg.push(silence_frame())          # 60 ms silence -> emit
    assert out is not None
    assert len(out) > 0


def test_too_short_speech_is_dropped():
    seg = Segmenter(silence_ms=40, min_speech_ms=100, is_speech=marker_is_speech)
    seg.push(speech_frame())                 # only 20 ms of speech
    seg.push(silence_frame())
    assert seg.push(silence_frame()) is None  # below min_speech_ms -> dropped
