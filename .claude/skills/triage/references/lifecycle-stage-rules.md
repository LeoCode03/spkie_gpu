# Lifecycle Stage Rules

## The canonical lifecycle

```
Intake → Spec → Plan → Build → Review → Close
```

Every Change Request passes through all six stages. Track and severity determine the **depth** of each stage, not which stages run.

---

## CR classification

### Types

| Type | When to use |
|---|---|
| `feature` | New behaviour, new module, new capability |
| `fix` | Bug in existing code |
| `security` | Vulnerability, auth gap, tenant isolation issue |
| `incident` | Production issue, data at risk, service degraded |
| `refactor` | Structural improvement, no behaviour change |

### Severity and track assignment

| Severity | Condition | Track | Stage depth |
|---|---|---|---|
| `Critical` | Production down, data at risk, active breach | Incident | Spec and Plan compressed and embedded into adjacent stages |
| `High` | Degraded service, significant impact, time-sensitive | Fast CR | Spec compressed to single-pass minimum viable depth |
| `Normal` | Everything else | Standard CR | All stages at full depth |

**Severity is inferred by the system, not requested by the human.** If the human's framing implies urgency or production impact, classify accordingly and confirm in the Intake gate.

### Rigor levels and pipeline by CR type

The rigor level is either inferred from CR type (standard behaviour) or explicitly set by the developer via `--rigor` flag at intake.

| Type | Rigor: fast | Rigor: standard (default) | Rigor: full |
|------|------------|--------------------------|------------|
| `feature` | spec lean (3 sections) → build → review → close | spec full → plan → build → review → close | spec full (all sections) → plan → build → review → close |
| `fix` | build → review → close (no spec) | spec lean (3 sections) → build → review → close | spec full → plan → build → review → close |
| `refactor` | build → review → close (no spec) | spec lean (3 sections) → build → review → close | spec full → plan → build → review → close |
| `security` | spec lean → build → review → close | spec full → plan → build → review → close | spec full → plan → build → review → close |
| `incident` | build (containment first) → review → close | build (containment first) → review → close | spec compressed → build → review → close |

**Spec lean** = 3 sections only: Problem Statement, Acceptance Criteria, Error Scenarios.
**Spec full** = all sections per `spec-quality-rules.md` proportionality table.
**No spec** (fast/fix, fast/refactor) = CR item contains the intent and ACs directly; build proceeds from that.

The rigor level is recorded in the CR item and governs every downstream stage.

---

## Stage rules

### Stage 1: Intake

- Accepts any input format
- Infers type and severity from the input; asks only when genuinely ambiguous
- Produces the CR item as its single artifact
- The human confirms assessment and intent — this is the only mandatory gate at this stage
- Does not advance without human confirmation

### Stage 2: Spec

**Standard and Fast tracks:**
- Reads the confirmed CR item
- Drafts a spec proportional to the CR's complexity
- Standard track: runs full Spec Review (domain correctness + structural integrity + security exposure — three perspectives in sequence, shared context)
- Fast track: runs compressed Spec Review (single-pass, focused on scope and acceptance criteria)
- Resolves all BLOCKER findings autonomously; asks human only for business decisions
- Does not advance until spec state reaches `SPEC_APPROVED`

**Incident track:**
- Spec is compressed and embedded into the Intake output as a problem-scope declaration
- Covers: what is broken, affected scope, immediate risk, and what a minimal fix looks like
- No standalone Spec Review; the containment framing in Build serves as the structural check

**Contract Impact Analysis (Standard and Fast tracks):**
After drafting the spec, the sw-architect perspective scans for modified contract surfaces.
If any are found:
- The spec cannot be approved until a Compatibility Decision is recorded
- Backwards compatible: Claude documents the technical approach (no consumer CRs needed)
- Breaking change: one consumer CR is created per dependent system before spec approval,
  following the protocol in `contract-impact-rules.md`
The Compatibility Decision is a `BUSINESS DECISION REQUIRED` marker — only the human can
confirm it. Once confirmed, Claude proceeds without further gates.

Contract Impact Analysis is skipped on the Incident track.

### Stage 3: Plan

- Reads the approved spec
- Identifies valid implementation approaches and presents trade-offs
- Recommends one approach clearly
- **Mandatory human gate: human confirms the recommended approach**
- Generates the layered blueprint and test skeletons after confirmation
- Re-assesses risk at implementation level; escalates to human if a new HIGH risk surfaces

**Incident track:**
- Plan is compressed and embedded into the Build preamble as a containment-then-fix framing
- Covers: immediate containment steps, scope of the minimal fix, layer affected
- No standalone Plan artifact on the Incident track; Build records the approach taken

### Stage 4: Build

- Reads plan, test skeletons, spec, and CR item
- Implements layer by layer: domain → application → outbound adapters → inbound adapters → config
- Runs tests after each layer; does not advance if a layer fails
- Does not invent structural decisions not covered by the plan; escalates material deviations
- Critical track opens with containment advice before writing any code
- Records all deviations from the plan in the Build summary

### Stage 5: Review (Post-Build)

- Evaluates the completed implementation, not the design
- Runs three mandatory perspectives in parallel: structural integrity, security exposure, operational impact
- Applies the shared severity model (see `review-severity-model.md`)
- Produces a clear verdict: `PASS` or `BLOCKED`
- All BLOCKER findings must be resolved before advancing to Close
- Review is never skipped, on any track

### Stage 6: Close

- Verifies all acceptance criteria are met and tests pass
- Produces the closure artifact reflecting actual outcome
- Surfaces lessons learned only when genuine and actionable
- Creates follow-up CRs for deferred items or discovered issues
- **Mandatory human gate: human confirms closure**
- Close is never skipped, on any track
- If the CR item has a `## Dependencies` section with `Produces:`: verify each listed consumer
  CR-ID exists as a `.cr.md` file in the working tree or appears in `BACKLOG.md`. If missing,
  create them using `contract-impact-rules.md` (anomaly path — annotate in closure artifact).
- Check whether the breaking change was actually delivered (present in build summary). If NOT
  delivered, close each consumer CR with a withdrawal note per `contract-impact-rules.md`.
- If the CR item has a `Triggered by:` field: read the producer CR's current status and include
  it in the closure artifact's Dependencies section.

---

## CR state machine

| State | Meaning |
|---|---|
| `OPEN` | CR created; awaiting Spec |
| `SPEC_DRAFT` | Spec being drafted |
| `SPEC_REVIEWED` | Spec review complete (full or compressed) |
| `SPEC_APPROVED` | All spec BLOCKERs resolved; ready to plan |
| `PLAN_READY` | Plan confirmed by human; ready to build |
| `IMPLEMENTING` | Build in progress |
| `REVIEWING` | Post-Build Review in progress |
| `CLOSED` | CR formally closed |

### State transitions by track

**Standard track:**
```
OPEN → SPEC_DRAFT → SPEC_REVIEWED → SPEC_APPROVED → PLAN_READY → IMPLEMENTING → REVIEWING → CLOSED
```

**Fast track** (Spec compressed, all states still recorded):
```
OPEN → SPEC_DRAFT → SPEC_APPROVED → PLAN_READY → IMPLEMENTING → REVIEWING → CLOSED
```

**Incident track** (Spec and Plan compressed into adjacent stages):
```
OPEN → SPEC_APPROVED → PLAN_READY → IMPLEMENTING → REVIEWING → CLOSED
```

### Transition rules

- No stage may advance the CR state without satisfying its gate condition and producing its required artifact.
- A CR in `REVIEWING` with unresolved BLOCKERs cannot transition to `CLOSED`.
- A CR in `CLOSED` state cannot be reopened. Discovered issues become new CRs.

---

## Human gates — summary

| Gate | Always mandatory | Conditional |
|---|---|---|
| Intake confirmation | Yes | — |
| Plan approach selection | Yes | — |
| Close confirmation | Yes | — |
| Business decision during Spec review | No | Triggered when a BLOCKER requires human authority |
| Risk escalation during Build | No | Triggered when material deviation or new HIGH risk surfaces |
| BLOCKER resolution during Review | No | Triggered when a BLOCKER requires a business trade-off |
| Compatibility decision during Contract Impact Analysis | No | Triggered when a public contract surface is modified and the change is assessed as breaking. Human decides: backwards compatible or breaking change. Claude owns all subsequent technical decisions (versioning approach, deprecation strategy, implementation pattern). |

---

## Predecessor enforcement

Each stage verifies its predecessor before running:

| Stage | Prerequisite |
|---|---|
| Spec | CR item exists and is in `OPEN` state |
| Plan | Spec artifact exists and CR is in `SPEC_APPROVED` state |
| Build | Plan artifact exists and CR is in `PLAN_READY` state |
| Review | Build summary exists and CR is in `IMPLEMENTING` state |
| Close | Review report exists with verdict `PASS` and CR is in `REVIEWING` state |

A stage that cannot confirm its prerequisite must stop and report the gap — it must not attempt to run anyway.
