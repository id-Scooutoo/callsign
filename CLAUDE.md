# callsign — project instructions

A Discord bot that wakes on its name, holds a short spoken conversation through a local LLM,
and answers in a supplied voice. STT, LLM and TTS all run on the operator's own machine.
Public repository (`id-Scooutoo/callsign`); the name, voice and personality are configuration,
never hardcoded to a person.

## Working preferences

- **Artifacts in English, chat in Polish.** Files (code, docs, configs, commits, PRs) are
  written in English. Conversation with the owner stays in Polish.
- **One step at a time, ELI5.** Small steps, confirm each before the next. Explain concepts in
  plain language with a tiny visual (ASCII/arrows) and as few words as possible.
- **Lean files.** Short and modular; one source of truth, link instead of duplicating.
- **Nothing personal ships.** This repo is public and the bot's whole point is that a
  conversation never leaves the machine. No real person's name, no voice sample, no voiceprint,
  no transcript, no token ever enters a commit. `persona.example.md` and `.env.example` are the
  only shapes that ship; the real ones are gitignored and stay that way.

## Conventions

- **Layout.** `src/callsign/` is the package (one module per concern: `wake`, `vad`, `stt`,
  `brain`, `tts`, `audio`, `discord_io`, `dialog_fsm`, `persona`, `config`); `tests/` mirrors
  it; `scripts/` holds one-shot tools; `deploy/` the bundle.
- **Heavy imports stay lazy or stay in their own module.** `src/callsign/stt.py` and
  `tts.py` import `faster_whisper` / `coqui-tts` / `torch` at module level and need a GPU —
  nothing else in the package may. `vad.py` is the pattern to copy: `import webrtcvad` inside
  the function that needs it, so the module imports anywhere.
- **Tests.** `pytest`. A test that needs the GPU or a heavy model carries `@pytest.mark.gpu`;
  if the whole file cannot be imported without one, it lives in `tests/test_stt.py` /
  `tests/test_tts.py`, which CI ignores by name. The command everything else runs:

  ```bash
  python -m pytest -q --ignore=tests/test_stt.py --ignore=tests/test_tts.py
  ```

  Locally, with the full venv: `pytest -q` (GPU tests included).
- **Text-only mode is a supported deploy, not a fallback.** `requirements-text.txt` is the
  minimal set for `VOICE_ENABLED=false`. A change that makes a voice-only dependency import at
  package level breaks that deploy — check it.

## Git workflow

Applies to **every** change, human or Claude.

- **Never commit to `main` directly.** Branch first, always. One logical change per branch.
- **Branch names:** `<type>/<short-slug>` matching the commit type — `feat/wake-vocative`,
  `fix/vad-frame-size`, `docs/readme-wsl`, `chore/deps`, `ci/portier`.
- **Commits: Conventional Commits.** Lowercase type, imperative, optional scope:
  `feat(wake): match instrumental case`. One coherent change per commit.
- **Check for conflicts on the branch, never on `main`:**

  ```bash
  git fetch origin
  git merge --no-commit --no-ff origin/main   # preview only; undo with: git merge --abort
  ```

- **Merge only via PR, approved by the owner.** @id-Scooutoo is the sole approver and merges
  every PR. Claude never self-merges and never pushes to `main`.
- **Commit and push only when the owner asks.** Draft the change, show it, wait for the go-ahead.
- **Never commit secrets.** `.env*`, `persona.md` and `voiceprint/` are gitignored — keep it
  that way.
- **CI:** `.github/workflows/ci.yml` runs the light pytest set on every PR. Green before merge.

## The portier

The delivery loop can drive itself: label a pull request `portier` and it is reviewed, fixed
against that review, and reviewed again until APPROVE or a cap of 5 rounds, at which point it
stops and calls the owner. It never merges and never casts a formal GitHub review. Ported from
MojRedmineGitlab, where the same loop lives in a Django backend.

Setup, rails and how to stop it: [`docs/PORTIER.md`](docs/PORTIER.md).

Building one task by hand — the BUILD node the loop's `implement` step mirrors — is
[`.claude/skills/do-task/`](.claude/skills/do-task/SKILL.md) (`/do-task`).

## Status

🚧 Working bot. Voice path needs an NVIDIA GPU (RTX 50-series needs a cu128 torch build);
text-only mode runs anywhere. Setup, Discord app config and the WSL/Ollama notes: `README.md`.
Deploy bundle: `deploy/DEPLOY.md`. Voice consent policy: `VOICE-CONSENT.md`.
