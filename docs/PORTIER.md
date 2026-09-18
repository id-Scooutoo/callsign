# The portier

A **duty officer for the delivery loop**: instead of a human asking for a review, reading the
verdict and asking for the fix, the repository does it itself and stops when a person is
actually needed.

```
label `portier` on a PR ─▶ review ─▶ verdict ─┬─ APPROVE         ─▶ stop, call the owner
                             ▲                └─ REQUEST CHANGES ─▶ fix ─┐
                             └──────────────────────────────────────────┘
                                       (capped at 5 reviews)
```

Ported from `id-Scooutoo/MyOwnGitlabRedmine`, where the driver is a Django module reading
GitHub webhooks (`backend/github/portier.py`) and the state lives in a `PortierRun` row. This
repository has no backend, so the decision runs in GitHub Actions and the state lives on the
pull request itself:

| MojRedmineGitlab | here |
| --- | --- |
| `Project.portier_enabled` + per-task handover | the `portier` label on ONE pull request |
| `PortierRun.rounds_used` | the `portier-round-<n>` label on that pull request |
| `PortierRun.waiting_for` | which event started the run; anything else resolves to "not your turn" |
| Django posts an `@claude` comment | the driver calls the action directly (see *Why no comment*) |

## The pieces

| file | what it is |
| --- | --- |
| `.github/workflows/portier-executor.yml` | the muscle, driven by a human: a comment starting with `@claude` under an issue or PR starts a session that answers in that thread |
| `.github/workflows/portier-driver.yml` | the loop: decides review / fix / stop, counts the rounds, calls the owner |
| `.github/portier/review.md` | the reviewer's prompt. Owns the `PORTIER VERDICT:` contract |
| `.github/portier/fix.md` | the fixer's prompt |
| `.github/workflows/ci.yml` | the light pytest gate the two prompts also run |

## Setup — three things, once

1. **The token.** On a machine with Claude Code:

   ```bash
   claude setup-token
   ```

   Put the result in *Settings → Secrets and variables → Actions → New repository secret*,
   named `CLAUDE_CODE_OAUTH_TOKEN`. It is the owner's subscription token, so the ceiling on
   cost is the subscription's own session limits — there is no per-run money cap to set.
   Per invocation the rails are `timeout-minutes: 30` and `--max-turns 60`.

2. **Keep one setting off.** *Settings → Actions → General → "Allow GitHub Actions to create
   and approve pull requests"* must stay **off** (GitHub's default). With `pull-requests: write`
   the workflow token can otherwise submit a real approving review — which is exactly the thing
   the owner alone is supposed to do. It is named here so it has an owner in writing rather than
   being an unwatched checkbox.

3. **Protect `main`.** Require a pull request and the owner's approving review before merge.
   Every other rail in this document assumes it.

## Using it

- **Hand a pull request over:** add the `portier` label. Nothing else starts it.
- **Take it back:** remove the label. The loop stops before the next step — a session already
  running finishes its turn and then nothing follows it.
- **One-off, no loop:** comment `@claude <what you want>` under an issue or a PR. That goes to
  the executor, answers in the thread, and starts no loop.
- **Watch it:** the `portier-round-<n>` label is the round counter. At 5 the loop stops with a
  comment and takes the `portier` label off itself.

## The rails, and why each exists

- **Default off, per pull request.** No label, nothing happens. There is no repository-wide
  switch on purpose.
- **A hard cap of 5 rounds**, checked at both moments a round would be spent — before a review,
  and before the fix whose whole purpose is to earn one. Checking only the first would let the
  last fix run a session nobody can ever review; checking only the second would let a cap of 0
  buy one review anyway. Change it in `portier-driver.yml` (`MAX_ROUNDS`).
- **It never merges and never approves.** APPROVE ENDS the loop; the merge is the owner's. The
  review job runs with `contents: read` and denies `gh pr review` / `gh pr merge` / `gh api` by
  name, so the verdict can only ever be a plain comment.
- **Fork pull requests are refused.** They carry no secrets anyway. Do not add a
  `pull_request_target` trigger to "fix" that — on a public repository it hands a fork's code
  the repository's own token and secrets.
- **Hosted runners only.** `ubuntu-latest`, never a self-hosted runner. MojRedmineGitlab runs
  its executor on a self-hosted VPS runner; that repo is private and the runner is its own box.
  A self-hosted runner attached to a public repository is reachable from any fork's pull
  request, and this repo shares no box with anything.

## Why the driver does not post an `@claude` comment

The original's Django driver starts a session by *commenting* `@claude …` as the project owner,
through their OAuth token. Here there is no such credential: a comment written with the
workflow token arrives as `github-actions[bot]`, and the executor's own `not a bot` guard would
throw it away — rightly, since without that guard the executor answers its own progress
comments in a loop. So the driver calls `anthropics/claude-code-action@v1` directly, with an
explicit `prompt:`, and the executor stays the human-driven door.

## The one thing that does not carry over

A push made with the workflow token starts no further workflow run. So the fix session's own
commits produce no `pull_request: synchronize`, and the driver cannot wait for one — which is
why `review` chains directly off `fix` inside a single run (`needs: [decide, fix]`) instead of
riding an event. The Django driver could wait, because a GitHub App receives that delivery
regardless.

Two consequences worth knowing:

- `ci.yml` does not re-run by itself on a fix session's commits. Re-run it with
  `gh run rerun`, or push anything by hand.
- A human's push to the branch *does* produce `synchronize`, and that starts a review round.

## The verdict line

`.github/portier/review.md` tells the reviewing session to end its comment with exactly one of:

```
PORTIER VERDICT: APPROVE
PORTIER VERDICT: REQUEST CHANGES
```

The driver matches that anchored at the start of a line, which is what lets the runbook quote
it without becoming a verdict. A missing or misspelled line stalls the pull request with nobody
being told — if a PR goes quiet mid-loop, read the last portier comment first.
