---
name: setup
description: >
  Configures the Praxis skills pack for an existing project. Scans the codebase,
  detects the stack and project size automatically, asks proportional questions,
  and writes ARCHITECTURE.md so all lifecycle skills have full context without
  re-scanning on every CR. Works with any language, framework, or project type.
  Usage: /setup
  Also use when: "configure this project", "update architecture snapshot".
  For new projects with no code yet, use /init instead.
  Do NOT use for: greenfield projects, anything other than existing project setup.
argument-hint: (no arguments needed)
---

# Setup — Existing Project

**Role: Project Configurator**
**Use on projects that already have code. For new projects, use `/init`.**

Scans the codebase once, detects the stack automatically, asks proportional
questions based on project size, and writes `CLAUDE.md` + `ARCHITECTURE.md`.
All lifecycle skills read these files instead of re-scanning on every CR.

Works with any language or framework — Python, TypeScript, Go, Rust, Flutter,
Rails, Django, or anything else.

---

## Step 1: Check for existing Praxis configuration

Read `CLAUDE.md` if it exists. Search for `Praxis Platform:`.

If found:
> "This project is already configured for `[platform]`. Re-running setup will
> re-scan the codebase and regenerate `ARCHITECTURE.md`. Continue? (yes / no)"

Wait. If no, stop.

---

## Step 2: Silent scan

Scan silently — no output during this step.

Look for any of these to understand the project type:
- `pyproject.toml`, `requirements*.txt`, `setup.py` → Python
- `package.json` → Node.js (check for `next`, `nest`, `express`, `fastify`, etc.)
- `pubspec.yaml` → Flutter/Dart
- `go.mod` → Go
- `Cargo.toml` → Rust
- `Gemfile` → Ruby/Rails
- `build.gradle`, `pom.xml` → Java/Kotlin
- Any other manifest → detect from contents

Read the directory tree 3 levels deep from the root (or `src/`, `lib/`, `app/`
whichever is the main source directory).

Read `tests/`, `test/`, `spec/`, or equivalent test directory structure.

After scanning, determine:

**Stack:** what language and framework this project uses (free text, e.g.
`python-fastapi`, `go-gin`, `rails`, `django`, `nestjs`, `nextjs`, `flutter`)

**Size:**

| Size | Signal |
|------|--------|
| **Tiny** | ≤3 feature areas, ≤1 external integration |
| **Medium** | 4–10 feature areas, 2–4 external integrations |
| **Large** | 10+ feature areas, 5+ integrations, OR custom IoC, OR multi-tenant |

---

## Step 3: Proportional interview

Ask questions one at a time and wait for each answer.

**Tiny — 1 question:**

> "Anything non-obvious about this project that a new engineer would likely
> misunderstand? (or: none)"

**Medium — 3 questions:**

> Q1: "What external services does it integrate with, and what is each used for?"

> Q2: "How are environment-specific dependencies configured?
> (e.g. env vars, config files per environment, custom IoC container)"

> Q3: "Any non-obvious parts — complex flows, async pipelines, dual databases,
> custom patterns — that aren't visible from the directory structure alone?"

**Large — 5 questions:**

> Q1: "List all external integrations and what each is used for."

> Q2: "How is environment-specific wiring handled?
> (e.g. YAML-driven IoC container, env vars, custom assembler, DI framework)"

> Q3: "Is this multi-tenant? If yes, how is tenant isolation enforced?
> (RLS, app-level filtering, separate DBs, or other)"

> Q4: "What are the non-obvious complexity hotspots?
> (e.g. two-phase writes, async workers, dual DBs, custom event buses,
> projection pipelines, state machines)"

> Q5: "Any architectural decisions that diverge from what the directory
> structure suggests? Things a new engineer would likely get wrong?"

---

## Step 4: Ask domain and gates

Ask these two questions, one at a time:

> **Q — Domain:** "What kind of work happens in this project primarily?
> - `software` — code, APIs, infrastructure, deployment
> - `content` — documents, writing, editing, marketing
> - `research` — investigation, analysis, literature review
> - `strategy` — decisions, planning, roadmaps
> - `general` — mixed or doesn't fit above
> (default: software)"

> **Q — Gates:** "Which lifecycle gates do you want active?
> All are on by default. Reply with any you want to disable:
> - `spec` — write a specification before planning
> - `plan` — produce an implementation plan before building
> - `review` — post-build code/output review
> - `lessons` — capture lessons learned at close
> (e.g. 'disable plan' or 'disable spec and review' — or 'all on')"

---

## Step 5: Write CLAUDE.md

**If no existing `Praxis Platform:` line:** append to `CLAUDE.md` (create if missing):

For `software` domain:
```
## Praxis Configuration

Praxis Platform:     <detected stack, e.g. python-fastapi, typescript-nestjs, go-gin>
Praxis Domain:       software
Praxis Gates:        spec=on, plan=on, review=on, lessons=on
Praxis TestCommand:  <detected test command, e.g. "pytest tests/ -v" or "npm test">
Praxis TestRunner:   <detected runner, e.g. pytest, jest, go test, rspec>
Praxis Language:     <detected language, e.g. python, typescript, go, ruby>
Praxis SourceRoot:   <detected source root, e.g. src/, app/, lib/>
Praxis FileExt:      <detected file extension, e.g. *.py, *.ts, *.go>
Praxis IsolationKey: <detected isolation field, or "none">
```

Detect each value from the scan:
- `Praxis TestRunner`: from manifest scripts or convention (`pytest` if pyproject.toml, `jest` if package.json has jest, `go test` if go.mod, etc.)
- `Praxis Language`: from the manifest type (pyproject.toml → python, package.json → typescript or javascript, go.mod → go, etc.)
- `Praxis SourceRoot`: the main source directory found during scan (`src/`, `app/`, `lib/`, `internal/` — whichever exists)
- `Praxis FileExt`: derived from language (`*.py`, `*.ts`, `*.go`, `*.rb`, `*.dart`, etc.)
- If a value cannot be detected, write `none` and note it in the confirmation message

For all other domains (`content`, `research`, `strategy`, `general`):
```
## Praxis Configuration

Praxis Domain: <domain>
Praxis Gates: spec=on, plan=on, review=on, lessons=on
```

`Praxis Platform:`, `Praxis TestCommand:`, and `Praxis IsolationKey:` are software-only fields — omit them entirely for non-software domains.

Adjust `Praxis Gates` based on the developer's answer. Example if they disabled plan:
`Praxis Gates: spec=on, plan=off, review=on, lessons=on`

**If replacing existing lines:** edit each line in-place.

---

## Step 6: Write ARCHITECTURE.md

Write `ARCHITECTURE.md` at the project root.

```markdown
# Project Architecture Snapshot
<!-- Generated: [date] — re-run /setup when architecture changes significantly -->
<!-- All Praxis lifecycle skills read this file instead of scanning the codebase. -->

## Stack
[detected stack — e.g. python-fastapi, go-gin, rails, nestjs, flutter]

## Project Size
[Tiny | Medium | Large] — [N feature areas, N external integrations]

## Directory Structure
[tree of main source directory — 3 levels deep, from scan]

## Feature Areas / Domains
[list of feature areas detected from scan]
[for each: one-line description of responsibility if inferrable]

## External Integrations
[from interview — each integration + what it's used for]
[if Tiny and none: "None detected"]

## Environment Configuration
[from interview — how env-specific wiring works]
[if Tiny and standard: "Standard env vars"]

## Multi-Tenancy
[from interview — isolation mechanism and where tenant ID is sourced]
[if not multi-tenant: "Single tenant"]

## Established Patterns
[patterns observed from scan:
 - naming conventions
 - base classes or mixins used consistently
 - any non-standard patterns observed]

## Complexity Hotspots
[from interview — the non-obvious parts]
[if Tiny and none: "None reported"]

## Architectural Notes
[from interview Q5 (Large) — divergences, surprises, things to know]
[if not Large or none reported: "None reported"]

## Test Structure
[from scan — test directory layout and naming conventions observed]
```

---

## Step 7: Install the enforce-spec-first hook

1. Check if `.git/` exists at project root. If not, skip silently.
2. Check if `.git/hooks/pre-commit` already exists.
   - Exists and not installed by Praxis: append (do not overwrite).
   - Does not exist: create it.
3. Write or append:

```bash
#!/bin/sh
# Praxis enforce-spec-first hook
# Blocks commits to feature code if no approved spec exists in specs/cr/

PROTECTED_DIRS="src/ app/ lib/ internal/ pkg/"
SPECS_DIR="specs/cr"

staged=$(git diff --cached --name-only 2>/dev/null)
if [ -z "$staged" ]; then exit 0; fi

has_violation=0
for dir in $PROTECTED_DIRS; do
  if echo "$staged" | grep -q "^$dir"; then
    has_violation=1
    break
  fi
done

if [ "$has_violation" -eq 0 ]; then exit 0; fi

if [ ! -d "$SPECS_DIR" ]; then
  echo "[Praxis] SPEC-FIRST VIOLATION: No specs/cr/ directory found."
  echo "[Praxis] Run /triage to create a CR before writing feature code."
  exit 1
fi

if ! grep -rl "SPEC_APPROVED" "$SPECS_DIR"/*.cr.md 2>/dev/null | grep -q .; then
  echo "[Praxis] SPEC-FIRST VIOLATION: No approved spec found."
  echo "[Praxis] Complete /spec <cr-id> before committing feature code."
  exit 1
fi

exit 0
```

4. `chmod +x .git/hooks/pre-commit`

---

## Step 8: Confirm

> **Praxis configured — [stack] — [Tiny | Medium | Large] project.**
>
> - Stack recorded in `CLAUDE.md`
> - Domain: `[domain]`
> - Gates: `[active gate list]`
> - Architecture snapshot written to `ARCHITECTURE.md`
>   - [N] feature areas documented
>   - [N] external integrations noted
>   - [N] complexity hotspots captured
> - Spec-first hook installed at `.git/hooks/pre-commit`
>
> All lifecycle skills will read `CLAUDE.md` and `ARCHITECTURE.md` instead of re-scanning.
> Re-run `/setup` when the architecture or gate configuration changes.
>
> Next step: `/triage <describe your first change request>`

---

## When to re-run setup

Re-run `/setup` when:
- A new major domain or feature area is added
- An external integration is added or removed
- The environment configuration strategy changes
- A significant structural refactor changes the directory layout

Do NOT re-run for individual CRs — `ARCHITECTURE.md` is a project-level snapshot,
not a per-CR artifact.
