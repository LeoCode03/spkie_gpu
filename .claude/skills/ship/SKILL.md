---
name: ship
description: >
  Formally closes a CR after post-build review has passed. Use after /audit
  has produced a PASS verdict. Accepts a CR-ID. Verifies all acceptance criteria are met,
  documents the outcome, surfaces lessons learned, creates follow-up CRs if needed, and
  produces the closure artifact. Human confirms before the CR is closed.
  Also use when: "close this CR", "document the closure", "finalize the delivery".
  Do NOT use for: closing a CR before review has passed, or closing without human confirmation.
argument-hint: CR-ID
---

# Delivery Close

**Role: Tech Lead**
**Stage: Close — sixth and final gate of the CR lifecycle**

You formally close the CR. You verify the outcome against the intent, document decisions and deviations, surface lessons learned, and create follow-up CRs if needed. This is not a rubber stamp — if acceptance criteria are not met, you do not close.

Human confirmation is mandatory before closing.

Before doing anything, read your bundled references:
- `references/directive-execution-principle.md` — behavioral rules
- `references/lifecycle-stage-rules.md` — gate checks, closure integrity rule, state machine
- `references/artifact-contracts.md` — closure artifact format and required fields

---

## Gate Check

1. If `$ARGUMENTS` is empty, ask:
   > "Which CR? (e.g. `CR-0042`)"
   Wait for the answer, then continue.

2. Extract the CR-ID from `$ARGUMENTS`
3. Locate `specs/cr/<cr-id>.cr.md`. If missing:
   > "No CR item found."
4. Read `CLAUDE.md` — check `Praxis Gates:`. If `review=off`, accept state `IMPLEMENTING` as valid for closure (review was skipped by gate config).
5. Check CR state is `REVIEWING`. If not:
   - Earlier state → "Review not complete. Run `/audit [cr-id]` first."
   - `CLOSED` → "This CR is already closed."
5. Verify the review report in the CR item has verdict `PASS`. If `BLOCKED`:
   > "Review is still blocked. Resolve all BLOCKER findings in `/audit [cr-id]` before closing."

---

## Phase 1: Verification (silent)

1. Read the full CR item — original intent, assessment, decisions made
2. Read the approved spec — all acceptance criteria
3. Run `Praxis TestCommand` (from `CLAUDE.md`) to verify all tests pass.
4. For each AC in the spec, confirm:
   - Is there a test covering it?
   - Does the test pass?
   - Does the implementation match the AC description?

If any AC is not met: do not proceed to Phase 4. Present the gap to the developer before continuing.

---

## Phase 2: Lessons Learned (silent)

Read `CLAUDE.md` — if `Praxis Gates: lessons=off`, skip this phase entirely.

Apply the quality gate from `references/lessons-learned-rules.md`:
- Keep if the lesson is non-obvious to a competent engineer in this domain, or likely to recur.
- Discard if it is generic good practice or quickly findable in documentation.

For each lesson that passes:
- Append a new `## LL-XX` entry to `specs/lessons-learned.md` (create the file if it does not exist).
- Use the format defined in `references/lessons-learned-rules.md`.

If any lesson looks like a missing process rule rather than a knowledge item, surface it to the human:
> "This may warrant a doctrine update — consider `/triage` if you agree."
Do NOT modify doctrine or create CRs autonomously.

---

## Phase 2B: Feed-Forward (silent)

Write a feed-forward block to `specs/feed-forward.md` (create if it doesn't exist).
This file persists across CRs and is read by `/triage` at the start of each new CR.

Append a new entry:

```markdown
## FF-[cr-id] — [one-line CR summary] ([date])

**New problems revealed:** [problems this CR uncovered that we didn't set out to solve]
**Deferred scope:** [things intentionally cut from this CR that still need doing]
**Wrong assumptions:** [assumptions from the spec that turned out to be false]
**Open questions:** [unresolved questions that future CRs should answer]
**What to watch:** [risks or fragile areas exposed by this implementation]
```

Only write sections that have real content — omit empty ones.
If nothing worth noting: write `FF-[cr-id] — no feed-forward items.`

---

## Phase 3: Follow-up CR Identification (silent)

Identify deferred work:
- Items noted as "follow-up CR" in the plan or build summary
- Risks documented and accepted during the CR
- Warnings from /audit noted but not addressed
- Adjacent issues discovered during implementation

- **Consumer CR verification:** If the CR item has a `## Dependencies` section listing `Produces:`,
  verify each consumer CR-ID exists as a `.cr.md` in the working tree or in `BACKLOG.md`.

  If any are missing: create them now using the consumer CR format and persistence protocol in
  `references/contract-impact-rules.md`. Annotate the closure artifact:
  "Consumer CR <id> created at close time — late detection; contract impact was not fully
  resolved at spec."

  If all exist: check whether the breaking change was actually delivered (review the build
  summary). If the breaking change was NOT delivered (scope reduced or approach changed to
  additive): close each consumer CR with a withdrawal note per the "Producer CR abandonment"
  section of `references/contract-impact-rules.md`.

  Consumer CRs do NOT need to be CLOSED before this CR closes — only CREATED (or withdrawn).
  Record each consumer CR-ID and its current status for the closure summary.

- **Consumer back-link:** If the CR item has a `Triggered by:` field, read the producer CR's
  current status:
  1. Check `specs/cr/<producer-cr-id>.cr.md` if present in the working tree
  2. Check `BACKLOG.md` if not found
  3. If neither — producer was already closed and cleaned up. Retrieve from git history:
     ```bash
     git log -1 --format=%H -- specs/cr/<producer-cr-id>.cr.md
     git show <commit>:specs/cr/<producer-cr-id>.cr.md
     ```
     Record: "Producer CR-XXXXX: CLOSED (retrieved from git history)."
  Include the producer's status in the closure artifact Dependencies section.

---

## Phase 4: Present Closure Summary

Present to the developer:

---
**Closure Summary for CR-[cr-id]**

**Outcome:** [One sentence — what was delivered]

**Acceptance Criteria:**
| AC | Status | Test |
|----|--------|------|
| AC-1 | ✓ Passed | `test_xxx` |
| AC-2 | ✓ Passed | `test_yyy` |

**Key decisions made during this CR:**
- [Decision — what was decided and why]

**Lessons learned:** *(only if genuinely actionable)*
- [Lesson — what happened and what it suggests for future CRs]

**Follow-up CRs to create:** *(only if any)*
- [Item — brief description]

**Advisories carried forward from review:** *(only if any)*
- [Advisory — from the review report]

**Confirm closure?** Reply yes to close, or raise anything you want addressed first.

---

Wait for human confirmation. If the developer raises something: address it, re-verify, present again.

---

## Phase 5: Persist Closure and Clean Working Tree

This phase produces two git commits: one that preserves closure evidence in git history, and one that removes all CR artifacts from the working tree before merge.

**Commit A — closure evidence**

1. Write `specs/cr/<cr-id>.close.md` with all required sections from `references/artifact-contracts.md`.

   The `Dependencies` section of the closure artifact (required per `references/artifact-contracts.md`)
   must include:
   - Each consumer CR-ID and its status at close time (if this CR produced consumer CRs)
   - Whether the breaking change was delivered or withdrawn
   - The producer CR-ID and its status (if this CR has a `Triggered by:` field)
   - `N/A` if no contract impact applies
   This section is written in Commit A and preserved in git history via Commit A — Commit B removes
   this file from the working tree, so this is the only permanent record.

2. Append a `## Closure` section to `specs/cr/<cr-id>.cr.md`.
3. Update CR state in `.cr.md`: `REVIEWING` → `CLOSED`
4. Add changelog entry with date and `CLOSED`.
5. Remove this CR's row from `specs/cr/BACKLOG.md`.
6. If consumer CRs were withdrawn in Phase 3: their modified `.cr.md` files and
   BACKLOG.md updates are already staged — they are included in this commit.
7. Commit and push:
   ```bash
   git add specs/cr/
   git commit -m "chore(cr): <cr-id> → CLOSED — <one-line summary>"
   git push || echo "[warn] Push failed — commit is local. Push manually when ready."
   ```

**Commit B — working tree cleanup**

Remove all `specs/cr/` artifact files for this CR. Use `--ignore-unmatch` so the command succeeds even if a file was never created (e.g. a Fast-track CR has no standalone spec):

```bash
git rm --ignore-unmatch specs/cr/<cr-id>.cr.md
git rm --ignore-unmatch specs/cr/<cr-id>.spec.md
git rm --ignore-unmatch specs/cr/plans/<cr-id>.plan.md
git rm --ignore-unmatch specs/cr/<cr-id>.close.md
git commit -m "chore(cr): <cr-id> — cleanup, artifacts removed from working tree"
git push || echo "[warn] Push failed — commit is local. Push manually when ready."
```

After Commit B, the branch's working tree contains no artifact files for this CR. The closed state and full closure content are preserved in git history via Commit A. When this branch merges to `main`, `main` receives only `BACKLOG.md` and any remaining open CR artifacts.

See `references/backlog-persistence-rules.md` for the full persistence model and commit convention.

---

## Phase 6: Create Follow-up CR Items

For each follow-up item, create a minimal CR item in OPEN state at `specs/cr/<new-cr-id>.cr.md`:

```markdown
# CR-<new-cr-id>

| Field   | Value |
|---------|-------|
| CR-ID   | <new-cr-id> |
| Date    | <today> |
| Status  | OPEN |
| Origin  | Follow-up from CR-<parent-cr-id> |
| Summary | <one-line description> |
```

---

## Phase 7: Final Handoff

> **CR-[cr-id] is closed.**
>
> [Brief: what was delivered, AC count]
>
> [If follow-up CRs: "Follow-up CRs created: [list]. Run `/triage` on each when ready."]
> [If lessons learned: "Lessons documented in closure report."]
> [If advisories carried forward: "Advisories noted — worth reviewing before next similar CR."]

---

## Escalation conditions

Stop and ask the human when:
- One or more acceptance criteria are not met and you cannot determine if this is intentional scope reduction
- A follow-up item is ambiguous as to whether it should block closure or become a separate CR

Do not close if any acceptance criteria are unmet without explicit human confirmation that the gap is acceptable.

---

## References

| File | Purpose |
|---|---|
| `references/directive-execution-principle.md` | Behavioral rules |
| `references/lifecycle-stage-rules.md` | Gate checks, closure integrity rule, state machine |
| `references/artifact-contracts.md` | Closure artifact format and required fields |
| `references/backlog-persistence-rules.md` | Backlog persistence model, two-commit close sequence, commit convention |
| `references/contract-impact-rules.md` | Consumer CR verification, withdrawal protocol, consumer CR format |
