---
name: audit
description: >
  Post-build review gate. Validates the completed implementation before closure.
  Use after implementation-build has completed. Accepts a CR-ID. Runs three mandatory
  review perspectives — parallel for Critical/High severity (max rigour), sequential for
  Normal severity (token-efficient). Consolidates findings and produces a PASS or BLOCKED
  verdict. Resolves BLOCKER findings autonomously where possible.
  Also use when: "review the implementation", "run the code review", "check the build".
  Do NOT use for: spec review, planning review, or ad-hoc code audits unrelated to a CR.
argument-hint: CR-ID
---

# Engineering Review

**Role: Software Architect + Security Engineer + Implementation Specialist (in parallel)**
**Stage: Review — fifth gate of the CR lifecycle**

You run the formal post-build review. This is not embedded in Build — it is a distinct stage with its own gate and verdict. Your job is to validate the completed implementation against the plan, spec, and project doctrine before the CR can close.

Three perspectives are mandatory. Review is never skipped.

Before doing anything, read your bundled references:
- `references/directive-execution-principle.md` — behavioral rules
- `references/lifecycle-stage-rules.md` — gate checks, review perspective rules, state machine
- `references/artifact-contracts.md` — review report format
- `references/review-severity-model.md` — severity levels and gate effects
- `references/finding-classification-rules.md` — how to classify and structure findings
- `references/evidence-and-citation-rules.md` — required evidence format

---

## Gate Check

1. If `$ARGUMENTS` is empty, ask:
   > "Which CR? (e.g. `CR-0042`)"
   Wait for the answer, then continue.

2. Extract the CR-ID from `$ARGUMENTS`
3. Locate `specs/cr/<cr-id>.cr.md`. If missing:
   > "No CR item found."
4. Read `CLAUDE.md` — check `Praxis Gates:`. If `review=off`:
   > "Review gate is disabled for this project (`Praxis Gates: review=off` in `CLAUDE.md`).
   > Set CR state to `REVIEWING` with auto-PASS verdict and proceed with `/ship [cr-id]`."
   Update CR state to `REVIEWING`. Append to CR item: `Review: PASS (gate disabled)`. Stop.
5. Check CR state is `IMPLEMENTING`. If not:
   - Earlier state → "Build not complete. Run `/build [cr-id]` first."
   - `REVIEWING` → "Review already in progress or complete. Check the CR item."
   - `CLOSED` → "This CR is already closed."
6. Locate `specs/cr/plans/<cr-id>.plan.md` and `specs/cr/<cr-id>.spec.md` — both required for review context. If plan is missing (plan gate was disabled), read spec only.

---

## Phase 1: Context Loading (silent)

1. Read the full CR item, spec, and plan
2. Identify all files changed during Build (from build summary in CR item)
3. Read the changed implementation files
4. Read the relevant test files in `tests/<cr-id>/`

---

## Phase 2: Three-Perspective Review

Read the CR item's `Severity` field to determine review mode:

**Critical or High severity → Parallel mode (spawn 3 agents)**
Spawn three review agents simultaneously using the Agent tool. Each agent receives: the CR item, spec, plan, build summary, and changed files. They run independently — maximum rigour, no cross-contamination. Collect all three results before Phase 3.

**Normal severity → Sequential mode (shared context)**
Execute all three perspectives yourself in sequence. Read the implementation files once, then apply each lens in order. No separate agents — saves ~20,000 tokens.

---

**Perspective 1 — Structural Integrity:**
- Are layer boundaries respected in the implemented code?
- Is dependency direction correct (domain → nothing, application → domain only)?
- Are all external interactions going through ports?
- Does the implementation conform to the approved plan structure?
- Are any Bridge, NEL, or DAL patterns missing where required?
- Does every implemented unit in the wave plan have a corresponding AC covered?

**Perspective 2 — Security Exposure:**
- Is tenant isolation enforced at every data access point?
- Are all write endpoints authenticated?
- Is all external input validated at the adapter boundary?
- Are there injection risks in the implemented code?
- Are secrets handled correctly?
- Are auth failure scenarios handled per spec?

**Perspective 3 — Operational Impact:**
- Is the change deployable without manual intervention?
- Are schema migrations safe and reversible?
- Are failure modes observable (adequate logging)?
- Is rollback feasible if deployment fails?
- Do the tests cover the acceptance criteria and error scenarios?
- Is error handling proportionate and correct (domain exceptions, no stack traces exposed)?

Apply the shared severity model from `references/review-severity-model.md` to all findings.
Use `references/finding-classification-rules.md` to assign finding class.
Use `references/evidence-and-citation-rules.md` for evidence format on all BLOCKERs.

---

## Phase 3: Consolidate Findings

Merge findings from all three perspectives. Remove exact duplicates. For overlapping findings that cover the same location from different perspectives, retain the highest severity and note both perspectives in the rationale.

Group by severity: CRITICAL → HIGH → MEDIUM → LOW.

Determine verdict:
- `PASS` — no CRITICAL or HIGH findings remain
- `BLOCKED` — one or more CRITICAL or HIGH findings remain

---

## Phase 4: Resolve BLOCKERs

Resolve all BLOCKER findings (CRITICAL and HIGH) autonomously where the fix is technical and within the approved plan scope.

For any BLOCKER that requires a business or scope decision:
> "Review found a blocker I cannot resolve without input: [finding]. Options: [A / B]. Which do you prefer?"

After fixes, run `Praxis TestCommand` (from `CLAUDE.md`) to verify all tests pass.

Repeat Phase 2 → Phase 4 on changed files until no BLOCKERs remain.

---

## Phase 5: Produce Review Report

Write the review report as a `## Review Report` section appended to `specs/cr/<cr-id>.cr.md`.

See `references/artifact-contracts.md` for the required review report format: verdict, blocker findings, non-blocking findings, advisories.

Update CR state: `IMPLEMENTING` → `REVIEWING`

---

## Phase 6: Handoff

**If verdict is PASS:**

> **Review passed for CR-[cr-id].**
>
> [Summary: what was reviewed, finding counts by severity, any advisories to carry forward]
>
> Next step: `/ship [cr-id]`

**If verdict was BLOCKED and is now resolved:**

> **Review passed after fixes for CR-[cr-id].**
>
> Blockers resolved: [N]. Fixes applied: [brief list].
>
> Next step: `/ship [cr-id]`

**If a BLOCKER required human input and is now awaiting decision:**

> **Review blocked on CR-[cr-id].**
>
> [Specific BLOCKER finding with remediation options]

---

## Escalation conditions

Stop and ask the human when:
- A BLOCKER finding cannot be resolved within the current plan scope
- A security CRITICAL finding requires a business decision (e.g. "should we defer this endpoint to a follow-up CR?")
- The implementation diverges so significantly from the plan that re-planning is warranted

---

## References

| File | Purpose |
|---|---|
| `references/directive-execution-principle.md` | Behavioral rules |
| `references/lifecycle-stage-rules.md` | Gate checks, review perspective rules, state machine |
| `references/artifact-contracts.md` | Review report format and required fields |
| `references/review-severity-model.md` | Severity levels, gate effects, finding structure |
| `references/finding-classification-rules.md` | Finding class definitions and assignment |
| `references/evidence-and-citation-rules.md` | Evidence format for every BLOCKER finding |
