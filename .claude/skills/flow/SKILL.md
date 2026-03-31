---
name: flow
description: >
  Fully automated CR pipeline — runs all remaining stages uninterrupted after resolving any
  business decisions upfront. Use after /triage has produced a CR item. Accepts a CR-ID.
  Clarifies all open business questions before starting, then runs spec → plan → build → audit → ship
  uninterrupted except for the mandatory Close confirmation. Informs on technical decisions; never asks
  about them. Resumes mid-pipeline CRs from the correct stage.
  Also use when: "run the full pipeline", "automate this CR", "let Claude handle it".
argument-hint: <cr-id>
user-invocable: true
---

# Flow — Automated Pipeline

**Role: Technical Lead**

You are responsible for running the full CR pipeline automatically. You own all technical decisions — you never ask the human to make a technical choice. You inform the human of technical decisions taken and why. You stop only when a genuine business decision is needed — one that requires context only the human can have.

---

## Gate Check

1. If `$ARGUMENTS` is empty:
   > "Which CR should I run? Provide a CR-ID (e.g. `CR-0001`)."
   Wait for the answer, then continue.

2. Locate `specs/cr/<cr-id>.cr.md`. If missing:
   > "No CR item found for <cr-id>. Run `/triage` first."
   Stop.

3. Read the CR item fully — intent, type, severity, acceptance criteria, assessment, changelog.

4. Determine resume stage from CR state:

| CR State | Resume at |
|---|---|
| `OPEN` | spec |
| `SPEC_DRAFT` or `SPEC_REVIEWED` | spec (continue from current sub-state) |
| `SPEC_APPROVED` | plan |
| `PLAN_READY` | build |
| `IMPLEMENTING` | build (continue from current sub-state) |
| `REVIEWING` | audit (continue) |
| `CLOSED` | nothing — report CR is already closed |

5. Report:
   > "CR-<cr-id> loaded. Resuming at: <stage>. Running pipeline to close."

---

## Phase 1: Business Clarification

Before starting the pipeline, identify every open business question across all remaining stages.

A business question is one where the answer requires context only the human can have:
- Business rules not inferable from the codebase or CR description
- Regulatory or compliance constraints
- Stakeholder priorities or deadlines
- Scope trade-offs with business impact (e.g. "defer X to keep the deadline?")

Technical questions are NOT business questions. If the answer can be determined from the codebase, the spec, the stack doctrine, or sound engineering judgement — Claude answers it.

**Clarification loop:**

1. Scan the CR item and the remaining stages for open business questions.
2. If none → skip to Phase 2 immediately.
3. If any → ask them all in one message. Be specific. For each question state why it blocks the pipeline.
4. Read the human's answers.
5. If any answer is incomplete or introduces new ambiguity → ask the follow-up questions only. Repeat until all business questions are resolved.
6. Confirm resolution:
   > "All business decisions are clear. Starting the pipeline now."

---

## Phase 2: Pipeline Execution

Execute each remaining stage in sequence by reading and following the stage skill's instructions exactly as if it had been invoked directly.

**Stage instructions are located at** (relative to the `.claude/skills/` directory where Praxis is installed):
- Spec: `skills/spec/SKILL.md`
- Plan: `skills/plan/SKILL.md`
- Build: `skills/build/SKILL.md`
- Audit: `skills/audit/SKILL.md`
- Ship: `skills/ship/SKILL.md`

If skills are not found at those paths, look for them at `.claude/skills/` or `skills/` relative to the project root.

For each stage:
1. Read the stage SKILL.md.
2. Execute its instructions in full for CR-<cr-id>.
3. When the stage completes, write a **Stage Handoff Summary** before proceeding:

   ```
   ## Stage Handoff: [stage name] → [next stage]
   - Artifact produced: [file path]
   - Key decisions made: [2-3 bullet points — only non-obvious choices]
   - Open items for next stage: [anything the next stage must be aware of, or "none"]
   - Context to discard: [what the next stage does NOT need from this stage's work]
   ```

   This summary is 100-150 tokens. The next stage reads this summary instead of the full conversation history from the previous stage. **Do not re-read prior stage conversation — read only: the CR item, the produced artifact, and the Stage Handoff Summary.**

4. Report: > "Stage <name> complete. Continuing to <next stage>."
5. Proceed to the next stage.

**Ship stage — mandatory confirmation:** When executing the ship stage, always present the closure summary and wait for human confirmation before proceeding to Phase 5. Do not skip this gate. The human must explicitly confirm before the CR is marked CLOSED. The only fast-path: if one or more acceptance criteria are unmet, stop immediately and surface the gap without producing a closure summary.

**Technical decisions encountered during execution:**
- Make the decision using codebase knowledge, stack doctrine, and engineering judgement.
- State the decision and reasoning inline:
  > "Two approaches considered: [A] and [B]. Taking [B] because [reason]. Proceeding."
- Never stop to ask.

**The only stop condition during pipeline execution:**
A question arises that was not resolved in Phase 1 and genuinely requires business context the human must provide. State the question and wait. On answer, continue immediately.

---

## Pipeline Complete

When all stages are done:

> **CR-<cr-id> is closed.**
> [One sentence: what was delivered]
> [Acceptance criteria: N/N met]
> [Technical decisions made: key choices with reasoning]
> [Follow-up CRs if created: list with CR-IDs]
