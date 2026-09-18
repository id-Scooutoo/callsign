---
name: do-task
description: Use when the owner hands over a GitHub issue to implement, types /do-task, gives an issue number/URL to "do", or asks to build/fix/implement something in callsign and open its PR. The BUILD node — turns an issue into a verified PR into main, then stops. Not for reviewing a PR (the portier does that) and not for merging.
---

# DO TASK

Turns one **GitHub issue** into a **verified PR into `main`**, grounded in the actual code and
following this repo's git workflow (CLAUDE.md). It stops at an open pull request. The **owner
is the gate**: never push to `main`, never self-merge.

After the PR is open, labelling it `portier` hands the review loop over to
[`docs/PORTIER.md`](../../../docs/PORTIER.md) — that is a separate decision, and the owner's.

**Hard rules — these are where this workflow actually breaks:**

- **Ground every change in source, not in the issue.** File:line references in an issue go
  stale. Open the real files and confirm current behaviour before changing a line. What you
  cannot verify is a visible `⚠️` note, never silent prose.
- **Check the blast radius before touching a shared helper.** `git grep` its callers first.
  `audio.py` and `wake.py` are used by both the voice and the text path — change at the
  **narrowest call site**, not the shared helper.
- **Heavy imports stay where they are.** Nothing outside `stt.py` / `tts.py` may import
  `torch`, `faster_whisper`, `coqui-tts` or `parselmouth` at module level — that breaks the
  text-only deploy (`requirements-text.txt`) and CI at once. `vad.py` is the pattern: import
  inside the function.
- **Test-first, always.** No production line without a failing test watched failing for the
  right reason. **REQUIRED SUB-SKILL:** superpowers:test-driven-development.
- **A changed spec means changed tests, not deleted assertions.** Tests that encoded the OLD
  behaviour get adapted to the new spec — never weakened to pass.
- **Nothing personal, ever.** Public repo: no real name, voice sample, voiceprint, transcript
  or token in the diff. If the issue asks for one, stop and ask.
- **Evidence before "done".** A claim of passing is backed by the actual test output, per
  superpowers:verification-before-completion.

## Steps

### 1. Read the issue and set the gate

```bash
gh issue view <N> -R id-Scooutoo/callsign --json title,body,labels,comments
```

Note what it actually asks for, including every negative criterion ("must not…", "stays
unchanged") — those become tests. If it is vague and the change is non-trivial, ask one
focused round before building rather than guessing.

### 2. Ground it in the code

Open the modules the issue touches and confirm current behaviour in source. For each
criterion, know exactly which function maps to it. `git grep` any helper you plan to change to
find every caller. Surface conflicts and ambiguities now, not after the diff exists.

### 3. Branch off fresh `main`

```bash
git fetch origin && git checkout -b <type>/<slug> origin/main
```

Always off the *latest* `origin/main`, never off the currently checked-out branch. `<type>` ∈
`feat|fix|docs|chore|ci`, picked by Conventional-Commits meaning — new user-visible behaviour
is `feat` even when the issue calls it a bug.

### 4. Implement test-first (red → green → adapt → refactor)

Write the failing test for a criterion, watch it fail for the right reason, write the
**minimal** code to pass. Then adapt any pre-existing test that encoded the old spec, and add
the negative criteria as their own tests. Smallest diff that satisfies the criteria — no
speculative abstractions, no unrequested scope.

### 5. Verify

```bash
python -m pytest -q --ignore=tests/test_stt.py --ignore=tests/test_tts.py
```

Green with pristine output. On a GPU machine with the full venv, run `pytest -q` as well when
the change touches `stt.py` or `tts.py` — CI cannot, and says so. Do not proceed on a red or
noisy suite.

### 6. Commit, push, open the PR

Conventional Commit, one coherent change. Confirm `git rev-list --count HEAD..origin/main` is
`0`, then:

```bash
git push -u origin <branch>
gh pr create -R id-Scooutoo/callsign --base main --head <branch> \
  --title "<conventional title>" --body "<what + why + how it was verified>"
```

The body is the brief the portier's reviewer will judge the diff against — say what the change
is for and how it was verified, not just what changed. Link the issue (`Closes #<N>`).

### 7. Hand off

Report the PR URL, criteria coverage, the real test output, and any decision left open. Do
**not** merge — the owner approves and merges every PR.

## Guardrails

- Never push to `main`; never self-merge; never `gh pr review`.
- Secrets never leave the environment — not in git, output, or an error message.
- Language: this skill + code + commits + PR in **English**; chat with the owner in **Polish**.
- One issue per branch; one coherent change per commit; the shortest diff that meets the criteria.
