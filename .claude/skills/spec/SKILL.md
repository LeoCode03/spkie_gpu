---
name: spec
description: >
  Produces a fully reviewed and approved specification for an open CR. Use after
  /triage has produced a CR item. Accepts a CR-ID. Drafts the spec
  proportional to the CR's complexity, runs multi-agent review (domain-analyst,
  sw-architect, security-engineer), resolves all blockers autonomously, and locks
  the approved spec. Asks the human only when a genuine business decision surfaces.
  Also use when: "write the spec", "spec this out", "draft the specification".
  Do NOT use for: planning, implementation, or review of code.
argument-hint: CR-ID
---

# Technical Spec

**Role: Domain Analyst + Software Architect + Security Engineer**
**Stage: Spec — second gate of the CR lifecycle**

You produce an approved specification for the CR. You draft it, review it through three mandatory perspectives, resolve all blockers autonomously, and lock it when approved. You ask the human only when a genuine business decision cannot be inferred.

Depth is proportional to the CR. You decide how much each section needs.

Before doing anything, read your bundled references:
- `references/directive-execution-principle.md` — behavioral rules
- `references/lifecycle-stage-rules.md` — gate checks, track rules, state machine
- `references/artifact-contracts.md` — required spec artifact format
- `references/spec-quality-rules.md` — required sections, quality checklist, blocker conditions

---

## Gate Check

1. If `$ARGUMENTS` is empty, ask:
   > "Which CR? (e.g. `CR-0042`)"
   Wait for the answer, then continue.

2. Extract the CR-ID from `$ARGUMENTS`
3. Locate `specs/cr/<cr-id>.cr.md`. If missing:
   > "No CR item found. Run `/triage` first."
4. Read `CLAUDE.md` — check `Praxis Gates:`. If `spec=off`:
   > "Spec gate is disabled for this project (`Praxis Gates: spec=off` in `CLAUDE.md`).
   > Set CR state to `SPEC_APPROVED` and proceed with `/plan [cr-id]`."
   Update CR state to `SPEC_APPROVED`. Stop.
5. Check CR state is `OPEN`. If:
   - `SPEC_DRAFT` or `SPEC_REVIEWED` → continue from current state
   - `SPEC_APPROVED` → "Spec already approved. Run `/plan [cr-id]`."
   - `PLAN_READY` or later → "This CR is past the spec stage."
5. Read the `Rigor` field from the CR item:
   - `fast` + type `fix` or `refactor` → no spec file needed; ACs and intent are in the CR item itself. Set state to `SPEC_APPROVED` and tell the developer: "CR is `fix`/`refactor` with `--rigor fast` — no spec required. Proceed with `/build [cr-id]`." Stop.
   - `fast` + type `feature` or `security` → produce lean spec (Problem Statement, Acceptance Criteria, Error Scenarios only).
   - `standard` → use proportionality table from `references/spec-quality-rules.md`.
   - `full` → produce full spec with all sections regardless of CR type.
   - If `Rigor` field is absent, treat as `standard`.
6. Check track from the CR item. For `Incident` track (regardless of rigor): produce a compressed problem-scope declaration (see §Compressed Spec below), then stop.

---

## Phase 1: Context Loading (silent)

1. Read the full CR item — type, severity, track, rigor, intent, assessment, decisions already made
2. Read `CLAUDE.md` — check `Praxis Domain:` and `Praxis Gates:` lines
3. Read `ARCHITECTURE.md` if it exists — use this as the project context instead of scanning `src/`
   - If `ARCHITECTURE.md` does not exist: scan the main source directory for related patterns as needed
4. Scan `specs/cr/` for related or dependent specs
5. If `specs/lessons-learned.md` exists, read it and surface any entries relevant to this CR

**Domain routing:**
- If `Praxis Domain: software` (or absent) → proceed to Phase 2 (Technical Spec)
- If `Praxis Domain: content | research | strategy | general` → proceed to Phase 2B (Plan Brief)

Decide proportionality: see `references/spec-quality-rules.md` proportionality table.

---

## Phase 2: Draft the Spec (software domain)

Update CR state to `SPEC_DRAFT`.

Create `specs/cr/<cr-id>.spec.md` using the required structure from `references/artifact-contracts.md`.

Annotation conventions:
- `(default)` — pre-decided technical default applied automatically
- `(inferred — verify)` — derived from context, flag for confirmation
- `BUSINESS DECISION REQUIRED` — blocks approval until resolved

Apply technical defaults from the stack reference (`references/stack-<platform>.md`) without asking. If no stack reference exists, apply defaults from `ARCHITECTURE.md` "Established Patterns" section. If neither exists, apply only what can be safely inferred from the CR description — flag anything uncertain with `(inferred — verify)`.

For sections not applicable to this CR type: write `N/A — [one-sentence justification]`.

---

## Phase 2B: Plan Brief (non-software domains)

*Only for `Praxis Domain: content | research | strategy | general`.*

Instead of a technical spec, produce a **Plan Brief** — a focused artifact that answers
8 questions about the work before execution begins.

Create `specs/cr/<cr-id>.spec.md` with this structure:

```markdown
# Plan Brief — CR-[cr-id]
Status: DRAFT | APPROVED
Date: [date]

## 1. Problem
What is the actual problem we're solving? (Not the solution — the problem.)
[One paragraph. Challenge vague answers — "we need a document" is a solution, not a problem.]

## 2. Goal
What does success look like when this is done?
[Concrete, observable outcome.]

## 3. Audience
Who is this for? What do they need from it?
[Specific — not "stakeholders" but who exactly and what they need to do with the output.]

## 4. Appetite
How much effort is this worth? What is the time/effort budget?
[Fixed budget: e.g. "2 hours", "one week", "one iteration". Not an estimate — a constraint.]

## 5. Acceptance Criteria
How will we know this is done and good enough?
[3-5 specific, verifiable criteria. Each must be checkable without subjective judgment.]

## 6. Constraints
What must we work within? What is explicitly out of scope?
[Hard limits: tools, formats, word counts, regulations, existing materials to reuse or avoid.]

## 7. Core Assumption
What is the single most important assumption this plan rests on?
[The thing that, if wrong, would invalidate the whole approach.]

## 8. Rabbit Holes to Avoid
What could pull us off track? What are we explicitly NOT doing?
[Known scope creep risks, tangents to decline, related work to defer.]
```

**Quality gate — challenge weak answers:**
- "We need to update the docs" → ask: "What happens if we don't? Who is blocked and how?"
- "Make it better" → ask: "Better how, measurable how, for whom?"
- Appetite left blank → ask: "How much time is this worth? Name a number."
- Acceptance criteria that are subjective → rewrite as verifiable checks

Run three review perspectives (same as Phase 4 for software):
1. **Clarity** — Is the problem real and specific? Are ACs verifiable?
2. **Feasibility** — Is the appetite realistic given the scope?
3. **Completeness** — Are rabbit holes named? Is the core assumption explicit?

Resolve all blockers. Approve when clean.

Update CR state to `SPEC_APPROVED`. Skip Phase 3 (contract impact is software-only).
Proceed to Phase 6 (handoff).

---

## Phase 3: Contract Impact Analysis (silent)

Read `references/contract-impact-rules.md` before this phase.

1. Scan for contract surfaces touched by this CR using the grep patterns in
   `references/contract-impact-rules.md`.

2. If no contract surface is touched:
   - Add `## Contract Impact` to the spec with:
     `N/A — no public contract surfaces are modified by this CR.`
   - Proceed to Phase 4.

3. If one or more contract surfaces are touched:
   a. Identify the exact surfaces: file, line, type (endpoint / event / port interface).
   b. Classify each change using the breaking-vs-additive rules in
      `references/contract-impact-rules.md`. When in doubt, classify as breaking.
   c. Scan for known dependents using the detection patterns in
      `references/contract-impact-rules.md`.
   d. If dependents cannot be determined from the codebase, ask once:
      > "Are there external systems or teams that consume [surface name]? List any you know of."
      Wait for answer; continue.
   e. If all changes are additive: document in `## Contract Impact` and proceed to Phase 4.
      No consumer CRs needed.
   f. If any change is breaking: present the `BUSINESS DECISION REQUIRED` gate:
      > **Contract Impact — Compatibility Decision Required**
      >
      > This CR modifies: [contract surface(s) — file:line, type]
      > Known dependents: [list]
      > Nature of change: [why it breaks existing consumers]
      >
      > **Option A — Backwards compatible:** [brief technical description]
      > **Option B — Breaking change:** Consumer CRs will be created for [list of dependents]
      >
      > Which approach?
      Wait for human answer. Once answered, continue immediately.

4. If breaking change confirmed:
   a. For each dependent system, create a consumer CR using the format in
      `references/contract-impact-rules.md`. Apply type/severity overrides if the producer
      CR is security or incident type.
   b. Follow the persistence protocol from `references/backlog-persistence-rules.md`:
      write `.cr.md`, add BACKLOG.md row, commit and push. The `git add specs/cr/` in
      the commit step covers both the consumer `.cr.md` files and the updated producer
      `.cr.md` — all are staged together before the commit.
   c. Add `## Dependencies` to the producer CR item (`specs/cr/<cr-id>.cr.md`):
      ```
      ## Dependencies
      Produces: CR-XXXXX, CR-YYYYY
      ```
   d. Report:
      > "Consumer CRs created: [list with CR-IDs]. Tracked in BACKLOG.md. Proceeding with spec."

5. Populate `## Contract Impact` in the spec file:
   - Contract surfaces modified (file:line, type)
   - Breaking: Yes / No
   - Known dependents (table: system, component, impact)
   - Compatibility decision (as confirmed, or "Additive — no decision required")
   - If breaking: consumer CRs created (table: CR-ID, system, status OPEN)

---

## Phase 4: Spec Review (three perspectives in sequence, shared context)

Once the draft is complete, review the spec through three mandatory perspectives in a single pass. Do not spawn separate agents — execute each perspective yourself in sequence, carrying full context across all three. This avoids reloading doctrine three times.

Read the spec draft once. Then apply each perspective against it:

**Perspective 1 — Domain correctness:**
- Is the problem statement clear and complete?
- Are all acceptance criteria testable (GIVEN/WHEN/THEN)?
- Are there missing edge cases?
- Are there ambiguities or vague terms?

**Perspective 2 — Structural integrity:**
- Are ports defined as interfaces, not implementations?
- Is the dependency direction correct?
- Are there boundary violations or missing ports?
- Is the bounded context correctly scoped?
- Is the Contract Impact section present and accurate? (surfaces identified, dependents listed,
  compatibility decision recorded — or explicitly N/A with justification)

**Perspective 3 — Security exposure:**
- If `Praxis IsolationKey` is set: is data isolation enforced for every data access path using that key?
- If `Praxis IsolationKey` is absent or "none": are there any implicit data ownership assumptions that need explicit access control?
- Are all write endpoints authenticated?
- Are there injection risks or unvalidated inputs?
- Is the security defaults section complete?

Consolidate all findings into a single list. Apply the shared severity model from `references/review-severity-model.md`.

---

## Phase 5: Revise

Resolve all BLOCKER and HIGH findings autonomously using the references and codebase context.

Ask the human only when:
- A blocker requires a business decision (e.g. "which roles may access this endpoint?")
- A `BUSINESS DECISION REQUIRED` field cannot be inferred

Ask one question at a time. Apply the answer and continue.

Repeat Phase 4 → Phase 5 until no blockers remain.

Update CR state to `SPEC_REVIEWED` after first successful review pass.

---

## Phase 6: Approve and Handoff

Update spec status to `APPROVED` in the spec file header.

Update `specs/cr/<cr-id>.cr.md`:
- State: `SPEC_REVIEWED` → `SPEC_APPROVED`
- Changelog: add entry
- Artifacts: link spec file

Tell the developer:

> **Spec approved for CR-[cr-id].**
>
> [One-paragraph summary: what the spec covers, key decisions made, any warnings noted]
>
> Next step: `/plan [cr-id]`

---

## Compressed Spec (Incident track)

For `Incident` track CRs, produce a compressed problem-scope declaration embedded into the CR item rather than a standalone spec file:

Append to `specs/cr/<cr-id>.cr.md` under a `## Problem Scope` section:
- What is broken or at risk
- Affected components and scope
- Immediate risk if unaddressed
- What a minimal fix looks like (one paragraph)

Set CR state to `SPEC_APPROVED` directly (no review loop).

Then tell the developer:
> "Problem scope documented. Proceed with `/build [cr-id]` for containment and fix."

---

## Escalation conditions

Stop and ask the human when:
- A `BUSINESS DECISION REQUIRED` field cannot be inferred from the input, codebase, or context
- A BLOCKER finding requires a scope trade-off only the human can make
- The spec's acceptance criteria are contradictory

Do not escalate for: technical pattern selection, default application, port placement, or anything the references define.

---

## References

| File | Purpose |
|---|---|
| `references/directive-execution-principle.md` | Behavioral rules |
| `references/lifecycle-stage-rules.md` | Gate checks, state machine, track rules |
| `references/artifact-contracts.md` | Required spec format and sections |
| `references/spec-quality-rules.md` | Quality checklist, blocker conditions, proportionality |
| `references/review-severity-model.md` | Severity levels and gate effects |
| `references/finding-classification-rules.md` | Finding classification |
| `references/evidence-and-citation-rules.md` | Evidence format for review findings |
| `references/contract-impact-rules.md` | Contract surface detection, breaking vs additive rules, consumer CR format |
| `references/backlog-persistence-rules.md` | Backlog write protocol for consumer CR creation |
