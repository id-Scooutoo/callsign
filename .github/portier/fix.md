Apply the code review on pull request #{pr} in this repository. Its branch `{branch}` is
already checked out here. The change is already built and has been reviewed — read the
verdict on the pull request and fix exactly what it asks for. Do not rebuild the change.

HOW TO WORK — FIX WHAT THE REVIEW ASKED FOR, DO NOT REBUILD THE CHANGE

- Read the whole verdict before touching anything:

      gh pr view {pr} --json title,body,comments,reviews
      gh pr diff {pr}

  The review summary, every inline review comment, every unresolved thread. Write down what
  is actually being asked for. If the newest review comment is the portier's own, its
  blockers are the list — the nits below them are optional and stay optional.
- Fix exactly those points, at the narrowest call site. Do not re-implement the change, and
  add no feature, refactor or scope the review did not ask for. A comment that looks wrong or
  unclear gets answered on the pull request, never guessed at.
- Test-first for every fix that changes behaviour: write the failing test the comment
  describes, watch it fail for the right reason, then write the minimal code that makes it
  pass. Never weaken or delete an existing test to make a comment go away.
- Run the tests before pushing, and paste the real output rather than claiming it:

      python -m pip install -q numpy soxr python-dotenv requests pytest pyyaml
      python -m pip install -q -e . --no-deps
      python -m pytest -q --ignore=tests/test_stt.py --ignore=tests/test_tts.py

  Those two files import `faster_whisper` and `coqui-tts` at module level and need a GPU, so
  they cannot run here. If your fix touches `src/callsign/stt.py` or `src/callsign/tts.py`,
  say so in your reply on the pull request — that part is unverified on this runner.
- Commit with a Conventional Commit message (`fix(scope): …`) and push to the SAME branch so
  the existing pull request updates:

      git add -A && git commit -m "fix(...): ..." && git push origin HEAD

  Never rebase, never amend a reviewed commit, no force-push: rewriting a branch under review
  invalidates every checkout and every comment anchored to it.
- Then reply on the pull request with `gh pr comment {pr}` saying what changed, point by
  point. Do NOT write a `PORTIER VERDICT:` line — you are not the reviewer; a review session
  runs straight after this one and writes the verdict.
- Never push to `main`, never merge the pull request, never `gh pr review` — the owner
  approves and merges every one.

If the review asks for something that would break a different feature, or the branch has
conflicts with `main`, stop and say so on the pull request instead of shipping a regression.
