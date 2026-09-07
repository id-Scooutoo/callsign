"""Text-triggered talking bot — interim mode while Discord voice RECEIVE is
blocked by DAVE E2EE (enforced 2026-03-02; discord-ext-voice-recv can't yet
decrypt inbound DAVE audio). Playback (DAVE send) works, so the bot joins a
voice channel and SPEAKS in the cloned voice, driven by text messages.

Commands (in a text channel the bot can see):
  !join          -> bot joins your current voice channel
  !leave         -> bot leaves
  !say <text>    -> speak <text> verbatim in the cloned voice
  <any message>  -> the configured persona (LLM) replies, spoken in the cloned voice
"""
import asyncio
import io
import os
import random
import re
import tempfile

import discord

from . import codesearch, imagegen, websearch
from .persona import load_persona

REACT_EMOJI = "cwel"  # server custom-emoji name to react with

_WR_INTENT = re.compile(
    r"projekt|zadani|task|issue|milestone|kamień|sprint|"
    r"co (jest )?(do zrobienia|robimy|w toku)|status\b|backlog|do zrobienia",
    re.IGNORECASE,
)
_CODE_INTENT = re.compile(
    r"gdzie (jest|siedzi|leży)|który (moduł|plik)|w którym pliku|"
    r"odpowiedzialn|odpowiada za|w kodzie|jak (jest )?zaimplement|klasa |funkcj",
    re.IGNORECASE,
)
_CREATE_ISSUE = re.compile(
    r"(?:za[łl][oó][żz]|dodaj|st[wó]rz|utw[oó]rz|nowe)\s+"
    r"(?:zadani\w*|task\w*|issue)\s+(?:w\s+(?P<slug>[\w-]+)\s*)?[:\-]?\s*(?P<title>.+)",
    re.IGNORECASE | re.DOTALL,
)

_DRAW_CAPTIONS = [
    "Masz, kurwa.",
    "No i git, patrz i się ucz.",
    "Zrobione, teraz zapierdalaj do roboty.",
    "Prezes narysował, doceń.",
    "Tu masz, i się kurwa nie czepiaj.",
]
_DRAW_TRIGGER = re.compile(
    r"^\s*(narysuj|naryzuj|wygeneruj\s+(?:obraz\w*|grafik\w*|mem\w*)|"
    r"zr[oó]b\s+(?:mi\s+)?(?:obraz\w*|grafik\w*|mem\w*)|poka[żz]\s+jak\s+wygl\w+)"
    r"\b[:,]?\s*",
    re.IGNORECASE,
)


class TextBot(discord.Client):
    def __init__(self, config, brain, tts, wr=None, **kw):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents, **kw)
        self.config = config
        self.brain = brain
        self.tts = tts
        self.wr = wr  # WhiteRabbit client or None
        self.vc: discord.VoiceClient | None = None
        self._lock = asyncio.Lock()
        self.last_reply = ""

    async def on_ready(self):
        print(f"logged in as {self.user} — ready (text mode)", flush=True)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        content = message.content.strip()
        print(
            f"[msg] {content!r} mention={self.user.mentioned_in(message)}", flush=True
        )

        if content == "!join":
            if self.tts is None:
                await message.channel.send(
                    "Głos wyłączony na tym hoście (VOICE_ENABLED=false)."
                )
                return
            if not message.author.voice:
                await message.channel.send("Wejdź najpierw na kanał głosowy.")
                return
            self.vc = await message.author.voice.channel.connect()
            await message.channel.send(
                "Wszedłem. Piszemy tekstowo. `!odp` = powiem ostatnią odpowiedź na VC · "
                "`!odp <tekst>` = odpowiem i powiem · `!say <tekst>` = powiem dosłownie · "
                "`!leave` = wyjdę."
            )
            print(f"joined VC '{message.author.voice.channel.name}'", flush=True)
            return

        if content == "!leave":
            if self.vc:
                await self.vc.disconnect()
                self.vc = None
                await message.channel.send("Wyszedłem.")
            return

        if content == "!reload":
            try:
                self.brain.persona = load_persona(self.config.persona_path)
                self.brain.history.clear()
                await message.channel.send("Persona przeładowana z persona.md.")
                print("[reload] persona reloaded", flush=True)
            except Exception as exc:  # noqa: BLE001
                await message.channel.send(f"Reload error: {exc}")
            return

        if content.startswith("!obraz ") or content.startswith("!rysuj "):
            await self._draw(message, content.split(" ", 1)[1].strip())
            return

        if content == "!projekty":
            await self._wr_list_projects(message)
            return
        if content == "!zadania" or content.startswith("!zadania "):
            await self._wr_list_issues(message, content[len("!zadania"):].strip() or None)
            return
        if content.startswith("!zadanie "):
            slug, _, title = content[len("!zadanie "):].strip().partition(" ")
            await self._create_issue(message, slug, title.strip())
            return

        # ----- voice commands (need TTS + an active VC) -----
        is_voice_cmd = (
            content == "!test"
            or content.startswith("!say ")
            or content == "!odp"
            or content.startswith("!odp ")
        )
        if is_voice_cmd and self.tts is None:
            await message.channel.send(
                "Głos wyłączony na tym hoście (VOICE_ENABLED=false)."
            )
            return

        if content == "!test":
            if not self.vc:
                await message.channel.send("Najpierw wejdź: !join.")
                return
            import soundfile as sf

            p = f"{self.config.voiceprint_dir}/clips/01.wav"
            data, srr = sf.read(p, dtype="float32")
            print("[test] playing clean reference clip", flush=True)
            async with self._lock:
                await self._play(data, srr)
            return

        if content.startswith("!say "):
            text = content[len("!say "):].strip()
            if not text:
                return
            if not self.vc:
                await message.channel.send("Najpierw wejdź: !join.")
                return
            await self._voice(text)
            return

        if content == "!odp" or content.startswith("!odp "):
            arg = content[len("!odp"):].strip()
            if arg:
                reply = await self._chat(message, arg)
                if reply is None:
                    return
            else:
                reply = self.last_reply
                if not reply:
                    await message.channel.send("Najpierw napisz coś, potem !odp.")
                    return
            if not self.vc:
                await message.channel.send("Najpierw !join, żebym powiedział na VC.")
                return
            await self._voice(reply)
            return

        # ----- default: text chat, only when the bot (user OR its role) is @mentioned -----
        me = message.guild.me if message.guild else None
        addressed = (
            self.user.mentioned_in(message) and not message.mention_everyone
        ) or (me is not None and any(r in message.role_mentions for r in me.roles))
        if addressed:
            query = re.sub(r"<@[!&]?\d+>", "", content).strip()
            if not query:
                return
            cre = _CREATE_ISSUE.match(query) if self.wr is not None else None
            if cre:
                await self._create_issue(
                    message, cre.group("slug"), cre.group("title").strip()
                )
                return
            draw = _DRAW_TRIGGER.match(query)
            if draw:
                await self._draw(message, query[draw.end():].strip())
            else:
                await self._chat(message, query)

    def _generate(self, text: str) -> str:
        """Gather context (web / White Rabbit / code) then reply (sync; executor)."""
        parts = []
        searched = False
        if websearch.needed(text):
            ctx = websearch.search_context(text)
            if ctx:
                parts.append(ctx)
                searched = True
        if self.wr is not None and _WR_INTENT.search(text):
            parts.append(self._wr_context(text))
        if self.config.code_repo_path and _CODE_INTENT.search(text):
            parts.append(codesearch.search(text, self.config.code_repo_path, wake_word=self.config.wake_word))
        context = "\n\n".join(p for p in parts if p)
        reply = self.brain.reply(text, context)
        # Fallback: if it says it can't check live info, search and retry once.
        if not searched and websearch.looks_unsure(reply):
            ctx = websearch.search_context(text)
            if ctx:
                if self.brain.history:
                    self.brain.history.pop()  # drop the unsure turn
                reply = self.brain.reply(text, ctx)
        return reply

    def _wr_context(self, text: str) -> str:
        try:
            projects = self.wr.list_projects()
        except Exception:  # noqa: BLE001
            return ""
        lines = ["Projekty w White Rabbit:"]
        for p in projects[:10]:
            lines.append(
                f"- {p.get('name')} (slug: {p.get('slug')}, rola: {p.get('my_role')})"
            )
        slug = self._pick_slug(text, projects)
        if slug:
            try:
                issues = self.wr.list_issues(project=slug)
            except Exception:  # noqa: BLE001
                issues = []
            lines.append(f"\nZadania w projekcie {slug}:")
            for i in issues[:20]:
                a = i.get("assignee")
                who = a.get("username") if isinstance(a, dict) else (a or "-")
                lines.append(
                    f"- #{i.get('number')} [{i.get('type')}/{i.get('priority')}/"
                    f"{i.get('status')}] {i.get('title')} (do: {who})"
                )
        return "\n".join(lines)

    @staticmethod
    def _pick_slug(text: str, projects: list) -> str | None:
        low = text.lower()
        for p in projects:
            slug = (p.get("slug") or "").lower()
            name = (p.get("name") or "").lower()
            if (slug and slug in low) or (name and name in low):
                return p.get("slug")
        return projects[0].get("slug") if projects else None

    async def _chat(self, message: discord.Message, text: str) -> str | None:
        loop = asyncio.get_running_loop()
        if message.guild:
            emoji = discord.utils.get(message.guild.emojis, name=REACT_EMOJI)
            if emoji:
                try:
                    await message.add_reaction(emoji)
                except Exception:  # noqa: BLE001 - missing "Add Reactions" perm etc.
                    pass
        async with message.channel.typing():  # shows the bot as typing while the LLM works
            try:
                reply = await loop.run_in_executor(None, self._generate, text)
            except Exception as exc:  # noqa: BLE001
                print("Brain error:", exc, flush=True)
                await message.reply(f"(LLM error: {exc})")
                return None
        self.last_reply = reply
        await self._send(message, reply)  # replies to the person who asked
        return reply

    async def _send(self, message: discord.Message, text: str) -> None:
        """Reply, splitting into <=1900-char messages (Discord's 2000 limit)."""
        limit = 1900
        if len(text) <= limit:
            await message.reply(text)
            return
        parts: list[str] = []
        cur = ""
        for line in text.split("\n"):
            while len(line) > limit:  # a single very long line
                if cur:
                    parts.append(cur)
                    cur = ""
                parts.append(line[:limit])
                line = line[limit:]
            if len(cur) + len(line) + 1 > limit:
                parts.append(cur)
                cur = line
            else:
                cur = cur + "\n" + line if cur else line
        if cur:
            parts.append(cur)
        for i, part in enumerate(parts):
            if i == 0:
                await message.reply(part)
            else:
                await message.channel.send(part)

    async def _voice(self, text: str) -> None:
        loop = asyncio.get_running_loop()
        print(f"[say] {text!r}", flush=True)
        async with self._lock:  # serialize playback
            try:
                wav, sr = await loop.run_in_executor(None, self.tts.speak, text)
                await self._play(wav, sr)
                print("[spoke]", flush=True)
            except Exception as exc:  # noqa: BLE001
                print("TTS/playback error:", exc, flush=True)

    async def _wr_list_projects(self, message: discord.Message) -> None:
        if self.wr is None:
            await message.reply("White Rabbit nie podłączony.")
            return
        loop = asyncio.get_running_loop()
        try:
            projects = await loop.run_in_executor(None, self.wr.list_projects)
        except Exception as exc:  # noqa: BLE001
            await message.reply(f"Błąd: {exc}")
            return
        if not projects:
            await message.reply("Zero projektów (konto bota nie jest członkiem żadnego).")
            return
        lines = [
            f"**{p.get('name')}** `{p.get('slug')}` — rola {p.get('my_role')}"
            for p in projects[:25]
        ]
        await self._send(message, "Projekty:\n" + "\n".join(lines))

    async def _wr_list_issues(self, message: discord.Message, slug) -> None:
        if self.wr is None:
            await message.reply("White Rabbit nie podłączony.")
            return
        loop = asyncio.get_running_loop()
        try:
            issues = await loop.run_in_executor(
                None, lambda: self.wr.list_issues(project=slug)
            )
        except Exception as exc:  # noqa: BLE001
            await message.reply(f"Błąd: {exc}")
            return
        where = f" w `{slug}`" if slug else ""
        if not issues:
            await message.reply(f"Zero zadań{where}.")
            return
        lines = [
            f"#{i.get('number')} [{i.get('status')}/{i.get('priority')}] {i.get('title')}"
            for i in issues[:30]
        ]
        await self._send(message, f"Zadania{where}:\n" + "\n".join(lines))

    async def _create_issue(self, message: discord.Message, slug, title: str) -> None:
        if self.wr is None:
            await message.reply("White Rabbit nie podłączony.")
            return
        if not title:
            await message.reply("Napisz tytuł zadania: `!zadanie <slug> <tytuł>`.")
            return
        loop = asyncio.get_running_loop()

        def do():
            s = slug
            if not s:
                ps = self.wr.list_projects()
                s = ps[0].get("slug") if ps else None
            if not s:
                raise RuntimeError("brak dostępnego projektu")
            return s, self.wr.create_issue(s, title)

        try:
            s, issue = await loop.run_in_executor(None, do)
        except Exception as exc:  # noqa: BLE001
            await message.reply(f"Nie udało się założyć: {exc}")
            return
        num = issue.get("number")
        root = self.config.wr_base_url.rsplit("/api", 1)[0]
        print(f"[wr] created #{num} in {s}", flush=True)
        await message.reply(
            f"Zrobione: [#{num} {title}]({root}/issues/{num}) w `{s}`. No i git."
        )

    async def _draw(self, message: discord.Message, prompt: str) -> None:
        if not prompt:
            await message.reply("No i co mam narysować, kurwa? Napisz co.")
            return
        loop = asyncio.get_running_loop()
        async with message.channel.typing():
            img = await loop.run_in_executor(
                None,
                imagegen.generate,
                self.config.openai_base_url,
                self.config.openai_api_key,
                self.config.image_model,
                prompt,
            )
        if not img:
            await message.reply("Nie wyszło, generator się kurwa zaciął.")
            return
        print(f"[draw] {prompt!r}", flush=True)
        f = discord.File(io.BytesIO(img), filename="callsign.jpg")
        await message.reply(random.choice(_DRAW_CAPTIONS), file=f)

    async def _play(self, wav, sr):
        """Write the utterance to a temp wav and let ffmpeg feed Discord.

        FFmpegPCMAudio does the 48k/stereo/framing that Discord's Opus encoder
        needs, which avoids the dropouts/buzz of hand-rolled PCM streaming.
        """
        loop = asyncio.get_running_loop()
        import soundfile as sf

        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        sf.write(path, wav, sr)
        while self.vc.is_playing():
            await asyncio.sleep(0.1)
        done = asyncio.Event()
        source = discord.FFmpegPCMAudio(path)
        self.vc.play(source, after=lambda e: loop.call_soon_threadsafe(done.set))
        try:
            await done.wait()
        finally:
            os.remove(path)
