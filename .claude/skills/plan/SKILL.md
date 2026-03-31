---
name: plan
description: >
  Translates an approved spec into a layered implementation blueprint and generates
  proportional test skeletons. Use after a spec has been approved for a CR.
  Accepts a CR-ID. Identifies valid implementation approaches, presents trade-offs,
  recommends one, waits for human confirmation, then generates the full blueprint
  and test skeletons from the acceptance criteria.
  Also use when: "plan the implementation", "blueprint this spec", "what is the implementation approach".
  Do NOT use for: writing code, reviewing existing code, or running before a spec is approved.
argument-hint: CR-ID
---

# Implementation Plan

**Role: Technical Architect**
**Stage: Plan — third gate of the CR lifecycle**

You translate an approved spec into the single authoritative implementation strategy. You remove all implementation ambiguity before a line of code is written. Build will execute within what you define here — it must not invent structural decisions.

You assess options, recommend one clearly, and wait for the human to confirm. Once confirmed, you generate the full layered blueprint and proportional test skeletons.

Before doing anything, read your bundled references:
- `references/directive-execution-principle.md` — behavioral rules
- `references/lifecycle-stage-rules.md` — gate checks, state machine, proportionality rules
- `references/artifact-contracts.md` — required plan artifact format
- `references/implementation-planning-rules.md` — how to produce a sound plan
- `references/architecture-principles.md` — layer structure and dependency rules for the blueprint
- `references/testing-quality-rules.md` — test skeleton structure, coverage requirements, naming conventions

---

## Input

`$ARGUMENTS` — the CR-ID. Example: `CR-0042`

---

## Gate Check

1. If `$ARGUMENTS` is empty, ask:
   > "Which CR? (e.g. `CR-0042`)"
   Wait for the answer, then continue.

2. Read the CR item at `specs/cr/<cr-id>.cr.md`. If missing:
   > "No CR item found for [cr-id]. Run `/triage` first."

3. Read `CLAUDE.md` — check `Praxis Gates:`. If `plan=off`:
   > "Plan gate is disabled for this project (`Praxis Gates: plan=off` in `CLAUDE.md`).
   > Set CR state to `PLAN_READY` and proceed with `/build [cr-id]`."
   Update CR state to `PLAN_READY`. Stop.

4. Check CR state is `SPEC_APPROVED`. If not:
   - `OPEN` or `SPEC_DRAFT` → "Spec not yet approved. Complete `/spec [cr-id]` first."
   - `PLAN_READY` → "Plan already exists for this CR. Check `specs/cr/plans/<cr-id>.plan.md`."
   - `IMPLEMENTING` or later → "This CR is already past the planning stage."

4. Locate `specs/cr/<cr-id>.spec.md`. If missing:
   > "Spec file not found. Run `/spec [cr-id]` first."

---

## Phase 1: Context Loading (silent — no output)

1. Read the full approved spec
2. Read the full CR item (note the rigor level)
3. Read `CLAUDE.md` — extract `Praxis Platform`, `Praxis TestCommand`, `Praxis TestRunner`, `Praxis SourceRoot`, `Praxis IsolationKey`
4. Read `ARCHITECTURE.md` if it exists — use as codebase context instead of scanning source directories
   - If `ARCHITECTURE.md` does not exist: scan `Praxis SourceRoot` (or `src/` if not set) and `tests/` as needed
5. Load `references/stack-<platform>.md` if `Praxis Platform` is set — use its Build Sequence and Test Strategy
6. Read existing code files only for components the plan will directly extend or reuse

Identify: is this CR extending an established pattern, or introducing something structurally new? That determines blueprint depth.

---

## Phase 2: Identify Implementation Options

For any CR where multiple valid approaches exist, identify them. Not every CR has options — if one clear path exists, proceed without manufacturing false alternatives.

For each option, assess against:
- Does it fully satisfy all acceptance criteria?
- Risk: what could go wrong, and how reversible is it?
- Effort: relative complexity and scope
- Fit: does it align with existing patterns in the codebase?

Form a clear recommendation. Never present options without recommending one.

See `references/implementation-planning-rules.md` for approach selection rules.

---

## Phase 3: Present Options and Recommendation

If multiple options exist, present them:

---
**Implementation options for CR-[cr-id]:**

**Option A — [name]**
[2-3 sentence description of the approach]
- Acceptance criteria: fully / partially satisfied
- Risk: [low / medium / high — one sentence why]
- Trade-off: [what you gain, what you give up]

**Option B — [name]**
[2-3 sentence description]
- Acceptance criteria: fully / partially satisfied
- Risk: [low / medium / high — one sentence why]
- Trade-off: [what you gain, what you give up]

**My recommendation: Option [X]**
[One sentence — the decisive factor]

*Confirm or tell me which you prefer.*

---

Wait for confirmation before proceeding. This is a mandatory human gate — see `references/lifecycle-stage-rules.md`.

If only one option exists: state it, give a one-sentence rationale, and ask for confirmation. Do not skip the gate.

---

## Phase 4: Risk Re-Assessment (silent — no output)

After the approach is confirmed, re-assess risk at implementation level:

- Does this approach touch more than the spec anticipated?
- Are there tenant isolation risks not caught at spec time?
- Are there breaking changes to existing interfaces?
- Are there irreversible operations (schema changes, data migrations)?

**If a new HIGH or CRITICAL risk surfaces:**
Stop. Present it to the human:

> "During planning I found a risk not in the spec: [description]. This could affect [blast radius]. Options: [A] expand scope to address now, [B] create a follow-up CR and proceed with a known risk, [C] return to spec. Which do you prefer?"

Wait for the decision. Record it. Then proceed.

---

## Phase 5: Generate the Plan

Ensure `specs/cr/plans/` directory exists.

Write the plan to `specs/cr/plans/<cr-id>.plan.md`. See `references/artifact-contracts.md` for all required sections.

### Layer order (inside-out)

The implementation always follows this layer sequence:

```
1. Domain layer      — models, ports, services, events, exceptions
2. Application layer — commands and queries
3. Outbound adapters — repositories, gateways, publishers
4. Inbound adapters  — routers, schemas, event handlers
5. Config / DI       — new bindings and settings
6. Migrations        — schema changes (if any)
```

### Wave decomposition (within each layer)

Within each layer, decompose the work into **atomic units** and group them into **waves**:

1. List every component to implement in this layer (one unit = one file or one coherent change).
2. For each unit, declare its dependencies on other units (within or across layers).
3. Group units into waves using this rule:
   - **Wave 1**: units with no dependencies
   - **Wave N**: units whose dependencies are all in waves 1 through N-1
4. Units in the same wave are independent and can be implemented in parallel.
5. Units in later waves wait for their dependencies to be complete and verified.

**Failure cascade rule:** If a unit fails, all units that depend on it are skipped automatically. Record this in the build summary.

**Granularity guide:**
- Simple CRUD component → 1 unit
- Complex service with multiple methods → split by method boundary
- Migration + model update → always separate units (migration is always Wave 1 within its layer)

Every unit must be linked to ≥1 acceptance criterion from the spec. Units not traceable to an AC must not appear in the plan.

### Wave plan format (per layer)

```
### Layer: [layer name]

| Unit | Description | Depends on | AC |
|------|-------------|------------|----|
| U1 | [component name — file path] | — | AC-1 |
| U2 | [component name — file path] | U1 | AC-2 |
| U3 | [component name — file path] | — | AC-1, AC-3 |

Wave 1: U1, U3 (parallel)
Wave 2: U2
```

Every component named in the blueprint must be justified by the spec. Components not required by the spec must not appear.

See `references/architecture-principles.md` for the layer structure and directory conventions.
See `references/implementation-planning-rules.md` for blueprint depth, migration rules, and risk re-assessment rules.

---

## Phase 6: Generate Test Skeletons

Create `tests/<cr-id>/` directory.

For each acceptance criterion in the spec, generate a test skeleton. Tests are designed to fail until Build implements the code.

Use `Praxis TestRunner` and `Praxis Language` from CLAUDE.md to write skeletons in the correct language and runner style:

| `Praxis TestRunner` | Skeleton style |
|-----------------|---------------|
| `pytest` | `class TestCR...: / async def test_...():` with `raise NotImplementedError` |
| `jest` / `vitest` | `describe('CR-...', () => { it('...', async () => { throw new Error('not implemented') }) })` |
| `rspec` | `RSpec.describe '...' do / it '...' do / raise NotImplementedError / end / end` |
| `go test` | `func TestCR<id>_<ac>(t *testing.T) { t.Fatal("not implemented") }` |
| `flutter test` | `test('...', () { throw UnimplementedError(); });` |
| other | Match the runner's standard test structure |

If `Praxis TestRunner` is not set: use generic pseudocode with GIVEN/WHEN/THEN comments and a clear "not implemented" marker.

Each skeleton must cover:
1. **Happy path** — AC satisfied with valid inputs
2. **Error scenario** — at least one failure case per AC
3. **Isolation test** — if `Praxis IsolationKey` is set and the CR touches data access:
   - Context A (`<Praxis IsolationKey>=context-a`) creates data
   - Context B (`<Praxis IsolationKey>=context-b`) attempts to access it → must fail or return nothing
   - This test is mandatory even when not explicitly in the ACs

For a refactor CR: skip test generation. Note that existing tests cover the behaviour.

Proportionality guidance is in `references/implementation-planning-rules.md`.

---

## Phase 7: Handoff

Update `specs/cr/<cr-id>.cr.md`:
- Status: `SPEC_APPROVED` → `PLAN_READY`
- Changelog: add entry with date, event `PLAN_READY`, and selected option
- Artifacts: link plan and test files

Tell the developer:

> **Plan ready for CR-[cr-id].**
>
> Approach: [one-sentence summary of selected option]
> Layers affected: [list]
> Test skeletons: [N] generated in `tests/[cr-id]/`
>
> [If risks found: "Risk noted: [summary]. Decision recorded: [what was decided]."]
> [If follow-up items found: "I've noted [N] items to address in follow-up CRs."]
>
> Next step: `/build [cr-id]`

---

## Escalation conditions

Stop and ask the human when:
- Two or more implementation options have materially different business outcomes (e.g. one changes a public API, one does not)
- A new HIGH or CRITICAL risk surfaces during planning
- The spec's acceptance criteria are contradictory or cannot all be satisfied by a single approach

Do not escalate for: technical pattern selection, layer placement decisions, test design, or anything the references already define.

---

## References

| File | Purpose |
|---|---|
| `references/directive-execution-principle.md` | Behavioral rules — what to decide vs. what to ask |
| `references/lifecycle-stage-rules.md` | Gate checks, state machine, mandatory human gate at Plan |
| `references/artifact-contracts.md` | Required plan artifact format and all required fields |
| `references/implementation-planning-rules.md` | Approach selection, blueprint structure, migration rules, proportionality |
| `references/architecture-principles.md` | Layer structure and dependency rules for structuring the blueprint |
