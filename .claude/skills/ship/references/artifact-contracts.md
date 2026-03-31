# Artifact Contracts

Every lifecycle stage produces exactly one canonical artifact. These contracts define the required content of each artifact. A stage that produces no artifact, or an artifact missing required sections, has not completed.

---

## CR Item

**Produced at:** Intake
**File:** `specs/cr/<cr-id>.cr.md`
**CR state set to:** `OPEN`

Required sections:

| Section | Content |
|---|---|
| CR-ID | Format `YYMMDD-HHMMSS` |
| Type | `feature` / `fix` / `security` / `incident` / `refactor` |
| Severity | `Critical` / `High` / `Normal` |
| Track | `Incident` / `Fast` / `Standard` |
| Rigor | `fast` / `standard` / `full` — set at intake via `--rigor` flag or inferred from type |
| Pipeline | The exact stage sequence for this CR, e.g. `spec (lean) → build → review → close` |
| Summary | One-line statement of the change |
| Intent | What success looks like — confirmed by the human |
| Assessment | Risk, blast radius, reversibility, impacted areas, dependencies |
| Initial risks | Known risks and assumptions at intake time |
| Recommended approach | The selected approach from intake Phase 4 — what to do first and why |
| Recommended next stage | The stage this CR should enter next |
| Dependencies | (Optional) Populated at spec time if this CR modifies a public contract surface.
                 Two formats:
                 Producer CR: `## Dependencies` section body — `Produces: CR-XXXXX, CR-YYYYY`
                 Consumer CR: `Triggered by: CR-XXXXX` header table field
                 Omit entirely if no contract impact. |

---

## Spec Artifact

**Produced at:** Spec
**File:** `specs/cr/<cr-id>.spec.md`
**CR state set to:** `SPEC_APPROVED`

Required sections (depth is proportional to CR complexity; no section may be omitted, but a section may be one sentence if genuinely trivial):

| Section | Content |
|---|---|
| Objective | What this change achieves and why |
| Problem statement | What is broken, missing, or insufficient |
| Scope | What is included in this change |
| Non-scope | What is explicitly excluded |
| Current state | How the affected area behaves today |
| Target state | How it must behave after this change |
| Constraints | Technical, business, or operational constraints that bound the design |
| Assumptions | Assumptions made where information was unavailable |
| Architecture implications | How this change interacts with existing layers, ports, and adapters |
| Acceptance criteria | Testable, unambiguous conditions that define done |
| Unresolved blockers | Business decisions or external dependencies not yet resolved |
| Contract Impact | CONDITIONAL — required if any public contract surface is modified; mark `N/A`
                   with one-sentence justification otherwise. Must include: contract surfaces
                   modified (file:line, type), breaking yes/no, known dependents, compatibility
                   decision, and — if breaking — consumer CRs created. |

---

## Plan Artifact

**Produced at:** Plan
**File:** `specs/cr/plans/<cr-id>.plan.md`
**CR state set to:** `PLAN_READY`

Required sections:

| Section | Content |
|---|---|
| Implementation goal | What the plan achieves, in one paragraph |
| Recommended approach | The selected implementation strategy |
| Rationale | Why this approach over the alternatives considered |
| Wave plan (per layer) | For each layer: table of units with dependencies and linked ACs, grouped into waves. Format: \| Unit \| Description \| Depends on \| AC \| — followed by "Wave N: [units]" groupings |
| Affected layers | Which layers and components are touched |
| Interface implications | New or changed ports, adapters, commands, queries, events |
| Test strategy | What types of tests, what coverage is expected |
| Migration notes | Schema changes, data migrations, rollback path |
| Risks | Implementation-level risks not present in the spec |
| Checkpoints | Where to stop and verify before proceeding |

Test skeletons are also produced at Plan, stored in `tests/<cr-id>/`.

**AC traceability rule:** Every unit in the wave plan must link to ≥1 acceptance criterion. Units not traceable to an AC must not appear. This ensures `/audit` can verify that all ACs have corresponding implementation units.

---

## Build Summary

**Produced at:** Build
**Embedded in:** Build output, referenced from CR item
**CR state set to:** `IMPLEMENTING`

Required sections:

| Section | Content |
|---|---|
| Implemented scope | What was actually built |
| Changed components | Files and modules modified or created |
| Tests added or updated | Test files and what they cover |
| Deviations from plan | Any material differences from the approved plan |
| Unresolved issues | Anything surfaced during build that was not resolved |

---

## Review Report

**Produced at:** Review (Stage 5 — Post-Build Review)
**Embedded in:** Review output, referenced from CR item
**CR state set to:** `REVIEWING`

Required sections:

| Section | Content |
|---|---|
| Review scope | What was reviewed (spec reference, plan reference, code paths) |
| Verdict | `PASS` or `BLOCKED` |
| Findings by severity | All findings grouped by CRITICAL / HIGH / MEDIUM / LOW |
| Required fixes | Every BLOCKER finding and its required remediation |
| Advisories | Non-blocking findings and recommendations |

Every finding must include: severity, finding class, exact location, rationale, concrete remediation.

A `BLOCKED` verdict means the CR cannot transition to `CLOSED` until all BLOCKER findings are resolved.

---

## Closure Artifact

**Produced at:** Close
**File:** `specs/cr/<cr-id>.close.md`
**CR state set to:** `CLOSED`

Required sections:

| Section | Content |
|---|---|
| Delivered scope | What was actually delivered |
| Implementation summary | Brief description of what was built and how |
| Deviations from spec or plan | Any material differences from the approved spec or plan |
| Final review state | Outcome of Post-Build Review; any advisories carried forward |
| Follow-up CRs | New CRs created from deferred items or discovered issues |
| Lessons learned | Genuine, actionable process improvements only — omit if none |
| Final status | `CLOSED` with date |
| Dependencies | If this CR produced consumer CRs: list each consumer CR-ID with its status
                 at close time, and whether the breaking change was actually delivered.
                 If producer abandonment occurred: note consumer CRs were closed with withdrawal.
                 `N/A` if no contract impact was identified during spec. |

---

## Artifact integrity rules

1. Artifacts are never modified retroactively after the stage that produced them, except to record deviations discovered in a later stage.
2. Every artifact references its CR-ID so the full trail is traceable.
3. The Closure artifact reflects the actual outcome — not the original intent.
4. A stage may not advance the CR state without producing its required artifact.

---

## Backlog persistence — Phase 1

In Phase 1, two lifecycle stages update `specs/cr/BACKLOG.md` and produce CR process commits:

| Stage | Action |
|-------|--------|
| Intake | Adds one row for the new CR. Commits `chore(cr): <cr-id> → OPEN — <summary>`. |
| Close | Removes the CR row. Commits closure evidence (Commit A: `→ CLOSED`), then removes all artifacts (Commit B: cleanup). |

Mid-lifecycle stages (`spec`, `plan`, `build`, `review`) do not yet produce backlog commits,
with two exceptions:
- `spec` creates consumer CRs for breaking contract changes and writes them to BACKLOG.md
- `close` creates consumer CRs in late-detection cases (anomaly path — annotated in closure artifact)
See `backlog-persistence-rules.md` for details.

See `backlog-persistence-rules.md` for BACKLOG.md format, commit convention, and push policy.
