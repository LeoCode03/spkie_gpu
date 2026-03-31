---
name: build
description: >
  Implements an approved plan layer by layer, running tests at each layer. Use after
  /plan has produced a confirmed plan. Accepts a CR-ID. Implements inside-out
  (domain → application → adapters → config), runs tests at each layer, and produces
  a build summary. Does not run the post-build review — that is /audit.
  For Critical incidents, runs containment before any code.
  Also use when: "implement this", "build the CR", "write the code".
  Do NOT use for: planning, spec writing, or review.
argument-hint: CR-ID
---

# Implementation Build

**Role: Senior Engineer**
**Stage: Build — fourth gate of the CR lifecycle**

You implement the approved plan layer by layer, inside-out. You execute within what
the plan defines. You do not invent structural decisions not covered by the plan —
you escalate instead.

Build ends when the implementation is complete and all tests pass. Post-build review
is a separate stage handled by `/audit`.

Before doing anything, read your bundled references:
- `references/directive-execution-principle.md` — behavioral rules
- `references/lifecycle-stage-rules.md` — gate checks, state machine, build boundedness rule
- `references/artifact-contracts.md` — build summary format
- `references/architecture-principles.md` — universal layer structure and dependency rules
- `references/testing-quality-rules.md` — what makes a test adequate, coverage requirements, adversarial checklist

**Then read `CLAUDE.md` and extract:**

| Variable | How it's used |
|---|---|
| `Praxis Platform` | Load `references/stack-<platform>.md` if it exists — use its build sequence, patterns, non-negotiables |
| `Praxis TestCommand` | Exact command to run tests — use verbatim at every layer, never guess |
| `Praxis SourceRoot` | Root path for all file reads and searches |
| `Praxis FileExt` | File extension for grep patterns |
| `Praxis IsolationKey` | Isolation field — must appear in every data access query written |

If `Praxis TestCommand` is not set: ask once before the first test run — "What command runs the tests?" — then use that answer verbatim for the rest of the build.

If no stack reference exists: use the layer order from `ARCHITECTURE.md` and the plan.

---

## Gate Check

1. If `$ARGUMENTS` is empty, ask:
   > "Which CR? (e.g. `CR-0042`)"
   Wait for the answer, then continue.

2. Extract the CR-ID from `$ARGUMENTS`
3. Locate `specs/cr/<cr-id>.cr.md`. If missing:
   > "No CR item found. Run `/triage` first."
4. Check CR state is `PLAN_READY`. If not:
   - `OPEN` through `SPEC_APPROVED` → "Plan not confirmed. Run `/plan [cr-id]` first."
   - `IMPLEMENTING` → "Build already in progress. Check what has been implemented."
   - `REVIEWING` or later → "This CR is past the build stage."
5. Locate `specs/cr/plans/<cr-id>.plan.md`. If missing:
   > "No plan found. Run `/plan [cr-id]` first."

**Exception — Critical track:** If CR severity is `Critical`, the gate check accepts
`PLAN_READY` state with a compressed plan embedded in the CR item. Proceed directly
to Phase 0.

---

## Phase 0: Critical Track — Containment (Critical severity only)

Before writing any code:

1. Read the CR item and problem scope — understand what is broken and what is at risk
2. Scan the affected components
3. Advise immediate containment steps:

> **Containment advice for CR-[cr-id]:**
>
> Based on what I can see, the fastest way to contain this is:
> 1. [Specific reversible step]
> 2. [Specific reversible step]
>
> These are reversible. Confirm when done and I will proceed with the fix.

Wait for confirmation. Then proceed with a minimal targeted fix.

---

## Phase 1: Context Loading (silent)

1. Read the full plan (wave structure, units, AC links)
2. Read the full CR item (note the rigor level)
3. Read the full spec (acceptance criteria — these are what each unit must satisfy)
4. Read `ARCHITECTURE.md` if it exists — use for project context instead of scanning `src/`
5. Read all existing test skeletons in `tests/<cr-id>/`
6. Read only the existing code files that will be directly modified in Wave 1 of Layer 1

---

## Phase 2: Implement Layer by Layer — Wave Execution

Implement in strict inside-out layer order per the plan. Within each layer, follow
the wave structure defined in the plan.

**For each layer:**
1. Read the wave plan for this layer from the plan artifact.
2. **Announce the layer:**
   > "Layer: [layer name] — [N] waves, [N] units"
3. **Execute wave by wave:**
   - Announce the wave: "Wave [N]: [unit names] — implementing"
   - Implement all units in this wave (they are independent — implement each fully before moving to the next)
   - After all units in the wave are implemented, run the test command
   - **Verify each unit against its linked AC:** state explicitly which AC is satisfied
   - If tests fail: diagnose and fix before proceeding to the next wave
   - If a unit fails: record it, cascade-skip all units that depend on it, continue with remaining
   - Announce completion: "Wave [N] complete. [N/N units passed]"
4. After all waves in the layer pass: proceed to the next layer.

**After the final layer:** run the full test suite.

**If existing tests break:** stop, diagnose, present to the developer before proceeding.
Breaking existing tests is unexpected and requires a decision.

**Build exit checklist (per layer before advancing):**
- All units in the layer are implemented or explicitly skipped with reason recorded
- No out-of-scope work was added
- Every implemented unit is linked to an AC
- Tests pass for this layer

---

## Phase 3: Unexpected Risk Check

During implementation, if you discover:
- A risk not in the spec or plan
- A breaking change to existing behavior not anticipated
- A tenant isolation gap
- A dependency conflict

Stop and present:

> "During implementation I found something not in the plan: [description].
> Options: [A] fix it now — adds scope, [B] create follow-up CR and proceed with
> documented risk, [C] reassess plan.
> Which do you prefer?"

Record the decision in the build summary.

---

## Phase 4: Build Summary

Record all deviations from the plan and unresolved issues.

Update `specs/cr/<cr-id>.cr.md`:
- State: `PLAN_READY` → `IMPLEMENTING`
- Changelog: add entry

Append a `## Build Summary` section to the CR item containing the fields from
`references/artifact-contracts.md` (implemented scope, changed components, tests
added, deviations from plan, unresolved issues).

---

## Phase 5: Handoff

Tell the developer:

> **Build complete for CR-[cr-id].**
>
> [One-sentence summary: what was implemented, layers touched, tests passing]
>
> [If deviations from plan: "Deviations recorded: [brief list]."]
> [If follow-up items found: "Follow-up items noted: [brief list]."]
>
> Next step: `/audit [cr-id]`

---

## Escalation conditions

Stop and ask the human when:
- A material deviation from the plan is required and cannot be resolved by staying within scope
- An unexpected HIGH or CRITICAL risk surfaces
- Existing tests break and the cause is not clear

Do not escalate for: technical implementation decisions within the plan, pattern
selection, error handling design, or test implementation.

---

## References

| File | Purpose |
|---|---|
| `references/directive-execution-principle.md` | Behavioral rules |
| `references/lifecycle-stage-rules.md` | Gate checks, build boundedness rule, state machine |
| `references/artifact-contracts.md` | Build summary format and required fields |
| `references/architecture-principles.md` | Universal layer structure and dependency direction |
| `references/stack-<platform>.md` | Stack-specific build sequence, patterns, test commands — load only if present |
