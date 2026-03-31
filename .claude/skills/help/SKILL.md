---
name: help
description: >
  Explains how the Praxis lifecycle works. Use when you want to understand what a
  skill does, what order to run them, how gates work, how to configure the project,
  or how to handle a specific situation. Answers any question about the Praxis system.
  Usage: /help
  Also use when: "how does this work", "what do I run next", "explain /spec",
  "what is a CR", "how do I configure gates", "what is the difference between /init and /setup".
argument-hint: (optional: topic or question)
---

# Praxis Help

**Role: Guide**

You explain the Praxis lifecycle clearly and concisely. Read `CLAUDE.md` first to
understand the project's current configuration (platform, domain, gates), then
answer in context.

If `$ARGUMENTS` is empty: show the full overview below.
If `$ARGUMENTS` contains a question or topic: answer it directly and specifically.

---

## Overview — What is Praxis?

Praxis is a lightweight lifecycle for managing engineering changes —
or any kind of work — with structure, traceability, and just enough process.

Every piece of work goes through a **CR (Change Request)**. A CR has a state that
advances through gates: Intake → Spec → Plan → Build → Review → Close.

Each gate produces an artifact. Each artifact is a Markdown file in `specs/cr/`.
Nothing moves forward without the previous gate completing.

---

## The Skills

### Setup skills (run once per project)

| Skill | When to use |
|-------|-------------|
| `/init` | Brand new project — no code yet. Interviews you, recommends a stack and architecture, writes `CLAUDE.md` + `ARCHITECTURE.md` as a blueprint. |
| `/setup` | Existing project — code already exists. Scans the codebase, asks proportional questions, writes `CLAUDE.md` + `ARCHITECTURE.md` as a snapshot. |

Run one of these before anything else. You only need to re-run when the architecture changes significantly.

---

### Lifecycle skills (run per CR, in order)

```
/triage → /spec → /plan → /build → /audit → /ship
```

| Skill | Stage | What it does | Input | Output |
|-------|-------|-------------|-------|--------|
| `/triage` | 1 — Triage | Classifies the change, assesses risk, produces a CR item | Anything: description, error log, file, URL | `specs/cr/<cr-id>.cr.md` |
| `/spec` | 2 — Specification | Drafts a spec, reviews it through 3 perspectives, locks it | CR-ID | `specs/cr/<cr-id>.spec.md` |
| `/plan` | 3 — Planning | Translates the spec into a layered build plan with waves | CR-ID | `specs/cr/plans/<cr-id>.plan.md` |
| `/build` | 4 — Implementation | Implements layer by layer following the plan | CR-ID | Code + tests |
| `/audit` | 5 — Review | Reviews the build: structure, security, correctness | CR-ID | Review report in CR item |
| `/ship` | 6 — Closure | Verifies ACs, captures lessons, feed-forward, closes the CR | CR-ID | `specs/cr/<cr-id>.close.md` |

---

### Shortcut skills

| Skill | When to use |
|-------|-------------|
| `/flow` | Runs the full pipeline (spec → plan → build → review → close) automatically from a CR-ID. Resolves business questions upfront, then runs uninterrupted. Use when you trust Claude to handle the whole pipeline. |
| `/craft` | Ad-hoc implementation, code review, refactoring, or debugging — outside of a CR. No lifecycle tracking. |

---

## Gates and rigor

Every CR has a **rigor level**. You almost never need to set it manually —
`/triage` reads what you describe and decides automatically:

| What you describe | How triage classifies it | Pipeline assigned |
|-------------------|--------------------------|-------------------|
| "the button is broken", "this crashes when…" | `fix`, Normal | lean spec → build → review → close |
| "add a new feature", "I want users to be able to…" | `feature`, Normal | full spec → plan → build → review → close |
| "refactor this module", "clean up the auth code" | `refactor`, Normal | lean spec → build → review → close |
| "security vulnerability in…", "user can access other accounts" | `security`, High | full spec → plan → build → review → close |
| "production is down", "critical error in…" | `incident`, Critical | containment → build → review → close |

**You only need `--rigor` when you want to override what triage would decide:**

| Flag | When to use it |
|------|---------------|
| `--rigor fast` | Intake would assign a full spec but you know the change is small. Forces lean or no spec, goes straight to build. |
| `--rigor full` | Intake would assign a lean pipeline but you want maximum rigour — all sections, full plan, full review. |
| `--rigor standard` | Explicit default. Same as not passing anything. |

**Example:**
```
/triage "add a contact modal"
```
→ Triage classifies as `feature`, assigns full spec. Fine for a real feature.

```
/triage --rigor fast "add a contact modal"
```
→ Same classification, but you're telling triage: "I know this is small, skip the spec."

**Rule of thumb:** don't pass `--rigor` at all. Let triage decide. Only override when you disagree with what it would choose.

---

## Configurable gates

Each gate can be turned off project-wide in `CLAUDE.md`:

```
Praxis Gates: spec=on, plan=on, review=on, lessons=on
```

Turn off gates you don't need for your project type:

| Example project | Suggested config |
|----------------|-----------------|
| Small script / personal tool | `spec=off, plan=off, review=off, lessons=on` |
| Content / writing project | `plan=off, review=off, lessons=on` |
| Full production software | all `on` (default) |
| Fast iteration / prototype | `spec=on, plan=off, review=on, lessons=off` |

When a gate is `off`, the skill detects it and skips automatically — you don't
need to remember.

---

## Domain

`Praxis Domain` in `CLAUDE.md` changes how `/spec` behaves:

| Domain | What /spec produces |
|--------|-------------------|
| `software` | Technical specification with ACs, architecture, security, contract impact |
| `content` | Plan Brief — 8 questions: problem, goal, audience, appetite, ACs, constraints, assumptions, rabbit holes |
| `research` | Plan Brief |
| `strategy` | Plan Brief |
| `general` | Plan Brief |

---

## Feed-forward

Every time a CR closes, `/ship` writes to `specs/feed-forward.md`:
- Problems revealed during the CR
- Scope that was deferred
- Assumptions that turned out to be wrong
- Open questions for future CRs

The next `/triage` reads the last 3 entries and surfaces anything relevant.
This keeps learning from one CR flowing into the next automatically.

---

## Files and directories

```
CLAUDE.md                        ← Praxis config: platform, domain, gates
ARCHITECTURE.md                  ← Project snapshot (generated by /setup or /init)
specs/
  cr/
    BACKLOG.md                   ← All open CRs in one table
    <cr-id>.cr.md                ← CR item (state, assessment, decisions)
    <cr-id>.spec.md              ← Specification or Plan Brief
    <cr-id>.close.md             ← Closure artifact (preserved in git history)
    plans/
      <cr-id>.plan.md            ← Implementation plan with waves
  lessons-learned.md             ← Accumulated lessons across all CRs
  feed-forward.md                ← Feed-forward items from recent CRs
```

---

## CR states

```
OPEN → SPEC_DRAFT → SPEC_REVIEWED → SPEC_APPROVED
     → PLAN_READY → IMPLEMENTING → REVIEWING → CLOSED
```

Each skill checks the state before running and tells you if something is out of order.

---

## Common questions

**"Where do I start?"**
Run `/init` (new project) or `/setup` (existing project). Then `/triage <describe your first change>`.

**"What if I just want to fix a small bug quickly?"**
Just describe it: `/triage fix the bug in X` — triage will classify it as a `fix` and assign a lean pipeline automatically. Only add `--rigor fast` if triage would classify it as something heavier (like a feature) but you know it's actually trivial.

**"Can I skip planning and just build?"**
Yes: set `plan=off` in `Praxis Gates`, or use `--rigor fast` on the CR. `/plan` will skip automatically.

**"I have a content/writing project, not code — does this work?"**
Yes. Set `Praxis Domain: content` and `Praxis Gates: plan=off, review=off`. You'll get a Plan Brief instead of a tech spec, and the lifecycle tracks your writing work the same way.

**"What is a wave?"**
In `/plan` and `/build`, work is broken into units and grouped into waves. Wave 1 = units with no dependencies (can run in parallel). Wave 2 = units that depend on Wave 1. This makes the build order explicit and prevents skipping dependencies.

**"The CR is stuck — how do I check its state?"**
Read `specs/cr/<cr-id>.cr.md` — the state is in the header table. Then run the skill for the current state.

**"How do I run the full pipeline automatically?"**
`/flow <cr-id>` — runs spec → plan → build → review → close uninterrupted. Asks only genuine business questions before starting.

---

## Quick reference card

```
New project:        /init
Existing project:   /setup
New change:         /triage [--rigor fast|standard|full] <description>
Write spec:         /spec <cr-id>
Plan build:         /plan <cr-id>
Build it:           /build <cr-id>
Review build:       /audit <cr-id>
Close CR:           /ship <cr-id>
Full pipeline:      /flow <cr-id>
Ad-hoc work:        /craft <task>
This help:          /help [topic]
```
