# Task prompt — callsign (auto-mode)

Paste the block below, append the task description at the end.

---

TASK: <describe the task here>

Run this end-to-end in auto-mode. Make every open decision yourself on best trade-off — do not
stop to ask unless a decision is destructive, irreversible, or changes the product's scope.
Start a stopwatch now (`date -Iseconds`) and report the actual wall-clock time spent at the end.

Environment (do not re-discover):

- Code, git and the bot run inside WSL: prefix those commands with
  `wsl -e bash -lc '...'`. Shell vars can silently expand to empty inside that wrapper —
  hardcode values or use a script file, and write anything with regex escapes to a file with
  the Write tool rather than through a shell one-liner.
- `gh` is installed and authenticated on the **Windows** side (Git Bash). Run every `gh` call
  through the plain Bash tool with an explicit repo flag, so no working directory is needed:
  `gh <cmd> -R id-Scooutoo/callsign`.
- Repo: `~/projects/callsign`. Public. Python package under `src/callsign/`.
- Tests without a GPU (what CI runs):
  `python -m pytest -q --ignore=tests/test_stt.py --ignore=tests/test_tts.py`
  Full suite, on the GPU machine with the real venv: `pytest -q`.
- Running the bot needs `.env` (from `.env.example`), Ollama reachable, and — for voice — the
  cu128 torch build. Text-only mode (`VOICE_ENABLED=false`) needs none of that.

## 1. Branch

`git fetch origin && git checkout -b <type>/<slug> origin/main` — always off the *latest*
`origin/main`, never off the currently checked-out branch. `<type>` ∈ feat|fix|docs|chore|ci and
matches the commit type (CLAUDE.md).

## 2. Analyse

One module per concern under `src/callsign/`, `tests/` mirrors it. Sweep before reading deep —
delegate the sweep to the `quick-search` agent (Haiku) to keep context cheap, then confirm the
exact logic at `file:line` before editing. No edit lands on an assumption.

Two traps specific to this repo:

- `stt.py` / `tts.py` import heavy GPU libraries at module level. Anything else that does
  breaks the text-only deploy and CI. `vad.py` shows the fix: import inside the function.
- `wake.py` is case-ending logic for Polish names, not a substring match. A "simplification"
  there is a regression — read the README section on it before touching it.

## 3. Plan

State: files to touch (in order), what each change does, how each step gets verified, what
could break. Effort proportional to difficulty. Then execute it.

## 4. Execute

Test-first where the logic is non-trivial (red → green → refactor). Match surrounding style.
Keep the diff minimal. Use `systematic-debugging` for anything non-obvious — hypothesis, then a
check that can disprove it, before any fix.

## 5. Guard gate (green before commit — paste real output, never claim from memory)

```bash
python -m pytest -q --ignore=tests/test_stt.py --ignore=tests/test_tts.py
```

Touched `stt.py` or `tts.py`? Then also the full `pytest -q` on the GPU machine, or say plainly
in the PR that that part is unverified.

## 6. Audit before commit

1. `/code-review high` on the working diff.
2. `/security-review` if the change touches the token, the voiceprint, `.env` handling, or
   anything that writes audio to disk.
3. Check the diff for a real person's name, a voice sample, a transcript or a token. Public repo.

Fix everything Critical/High, re-run the gate.

## 7. Commit · push · PR

Conventional Commits, imperative, one coherent change per commit. Before proposing the merge,
check for conflicts on the branch, not on main:

```bash
git fetch origin && git merge --no-commit --no-ff origin/main   # undo with: git merge --abort
```

Push from WSL, then open the PR with `gh` from the Windows shell:

```bash
gh pr create -R id-Scooutoo/callsign --base main --head <branch> \
  --title "<conventional title>" --body "<what + why + how it was verified>"
```

The PR body is the brief the portier's reviewer judges the diff against — write it for a
reviewer, not as a changelog. Never push to `main`, never self-merge — @id-Scooutoo approves and
merges every PR.

## 8. CI and the review loop

```bash
gh pr checks <n> -R id-Scooutoo/callsign
```

Red check → pull the failing job's log (`gh run view <run-id> --log-failed -R …`), fix on the
branch, push, re-poll. Do not hand over a PR with a red check.

Then, if the owner wants the loop: they label the PR `portier` and the review/fix rounds run by
themselves (`docs/PORTIER.md`). Do not add that label yourself — handing a PR over is the
owner's decision.

## 9. Report

- PR link.
- What changed, in one paragraph.
- Gate evidence (real command output, not a claim).
- CI status on the PR.
- Actual wall-clock time spent.
