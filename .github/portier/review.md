Code-review pull request #{pr} in this repository (branch `{branch}`). The code is already
written and waiting for a verdict — judge it. Do not change the code yourself.

HOW TO WORK — REVIEW THE PR, DO NOT CHANGE THE CODE

- Read the diff first: `gh pr diff {pr}` and `gh pr view {pr} --json title,body,comments`.
  Its body is the brief. If the body does not say what the change is for, say so in the
  verdict rather than inventing a brief for it.
- Judge the diff against that brief: does it do what it claims, including the negative cases
  ("must not…", "stays unchanged")? Name each point it leaves unmet, and cite `file:line`
  for every finding.
- Judge it against this repo's own standards (CLAUDE.md): tests written for the behaviour
  that changed, no unrequested scope, no dead code, the change made at the narrowest call
  site, nothing about a conversation leaving the machine, no secret or token in the diff,
  no real person's name or voice data added to the repository.
- Ground the verdict by running the tests yourself rather than predicting them:

      python -m pip install -q numpy soxr python-dotenv requests pytest pyyaml
      python -m pip install -q -e . --no-deps
      python -m pytest -q --ignore=tests/test_stt.py --ignore=tests/test_tts.py

  Those two files are ignored on purpose: they import `faster_whisper` and `coqui-tts` at
  module level and need a GPU, so they cannot run on this runner. If the diff touches
  `src/callsign/stt.py` or `src/callsign/tts.py`, say in the verdict that their tests were
  NOT run here — do not imply coverage this runner cannot give.
- Do not fix anything: no commits, no pushes, no edits on the author's branch, no branch of
  your own. Every finding is `file:line` + what is wrong + what to do instead, and blockers
  are kept apart from nits.

HOW TO DELIVER IT

Post ONE comment with `gh pr comment {pr} --body-file <file>`. Never `gh pr review`, never
`gh api` — those cast a real, binding GitHub review, and only the owner casts one.

The comment ends with exactly one of these two lines, alone on its own line, as the very last
line, spelled exactly like this:

    PORTIER VERDICT: APPROVE
    PORTIER VERDICT: REQUEST CHANGES

That line is not decoration — `.github/workflows/portier-driver.yml` matches it to decide
whether the loop runs another round or stops. Do not write it anywhere else in the comment,
do not quote it in an example, and do not add a third spelling: a missing or misspelled line
stalls the pull request with nobody being told.

REQUEST CHANGES means there is at least one blocker. Nits alone are an APPROVE with the nits
listed. Never merge the pull request — the owner approves and merges every one.
