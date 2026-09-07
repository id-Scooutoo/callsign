import asyncio
import io
import time

import discord
from discord.ext import voice_recv

from .audio import float_to_int16, mono_to_stereo, resample_int16, stereo_to_mono
from .dialog_fsm import State
from .vad import FRAME_BYTES, Segmenter

DISCORD_RATE = 48000


class UserStream:
    """Per-user: buffer 48k-stereo -> 16k-mono frames -> VAD -> utterance queue."""

    def __init__(self, out_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.seg = Segmenter(aggressiveness=2, silence_ms=600, min_speech_ms=300)
        self.buf = bytearray()
        self.out_queue = out_queue
        self.loop = loop

    def feed(self, pcm48_stereo: bytes) -> None:
        mono48 = stereo_to_mono(pcm48_stereo)
        mono16 = resample_int16(mono48, DISCORD_RATE, 16000)
        self.buf.extend(mono16)
        while len(self.buf) >= FRAME_BYTES:
            frame = bytes(self.buf[:FRAME_BYTES])
            del self.buf[:FRAME_BYTES]
            utt = self.seg.push(frame)
            if utt is not None:
                self.loop.call_soon_threadsafe(self.out_queue.put_nowait, utt)


class _BytesReader(io.RawIOBase):
    def __init__(self, data: bytes):
        self._data = memoryview(data)
        self._pos = 0

    def read(self, n=-1):
        if n is None or n < 0:
            n = len(self._data) - self._pos
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return bytes(chunk)

    def readable(self):
        return True


class VoiceBot(discord.Client):
    def __init__(self, config, brain, stt, tts, fsm, wake_fn, **kw):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents, **kw)
        self.config = config
        self.brain = brain
        self.stt = stt
        self.tts = tts
        self.fsm = fsm
        self.wake_fn = wake_fn
        self.utterances: asyncio.Queue = asyncio.Queue()
        self.streams: dict[int, UserStream] = {}
        self.vc: voice_recv.VoiceRecvClient | None = None

    async def on_ready(self):
        print(f"logged in as {self.user} — ready", flush=True)

    async def join(self, channel: discord.VoiceChannel):
        self.vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
        loop = asyncio.get_running_loop()

        def on_audio(user, data):
            if user is None:
                return
            stream = self.streams.get(user.id)
            if stream is None:
                stream = UserStream(self.utterances, loop)
                self.streams[user.id] = stream
            stream.feed(data.pcm)

        self.vc.listen(voice_recv.BasicSink(on_audio))
        loop.create_task(self._worker())
        print(f"joined VC '{channel.name}' — say the wake word", flush=True)

    async def _worker(self):
        loop = asyncio.get_running_loop()
        while True:
            utt = await self.utterances.get()
            now = time.monotonic()
            self.fsm.tick(now)
            try:
                text = await loop.run_in_executor(None, self.stt.transcribe, utt)
            except Exception as exc:  # noqa: BLE001 - stay responsive on STT error
                print("STT error:", exc, flush=True)
                continue
            if not text:
                continue
            print(f"[{self.fsm.state.name}] heard: {text!r}", flush=True)
            if self.fsm.state == State.SLEEPING:
                if self.wake_fn(text, self.config.wake_word):
                    self.fsm.on_wake(now)
                    print("[wake] -> LISTENING", flush=True)
                continue
            self.fsm.on_utterance(now)
            try:
                reply = await loop.run_in_executor(None, self.brain.reply, text)
            except Exception as exc:  # noqa: BLE001 - Ollama down: skip turn
                print("Brain error:", exc, flush=True)
                self.fsm.on_reply_done(time.monotonic())
                continue
            print(f"[reply] {reply!r}", flush=True)
            self.fsm.on_reply_start()
            try:
                wav, sr = await loop.run_in_executor(None, self.tts.speak, reply)
                await self._play(wav, sr)
                print("[spoke]", flush=True)
            except Exception as exc:  # noqa: BLE001 - TTS/playback error: skip
                print("TTS/playback error:", exc, flush=True)
            self.fsm.on_reply_done(time.monotonic())

    async def _play(self, wav, sr):
        loop = asyncio.get_running_loop()
        pcm16_mono = float_to_int16(wav)
        pcm16_mono48 = resample_int16(pcm16_mono, sr, DISCORD_RATE)
        pcm48_stereo = mono_to_stereo(pcm16_mono48)
        source = discord.PCMAudio(_BytesReader(pcm48_stereo))
        done = asyncio.Event()
        self.vc.play(source, after=lambda e: loop.call_soon_threadsafe(done.set))
        await done.wait()
