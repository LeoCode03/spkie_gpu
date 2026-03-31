---
name: init
description: >
  Configures the Praxis skills pack for a brand new project with no code yet.
  Interviews the developer to understand what they are building, recommends
  the right platform and architecture, and writes CLAUDE.md + ARCHITECTURE.md
  as a forward-looking blueprint. Proportional to project size — tiny projects
  get a short interview, large ones get a full design session.
  Usage: /init
  Also use when: "start a new project", "scaffold this project", "set up from scratch".
  For existing projects that already have code, use /setup instead.
  Do NOT use for: projects that already have code.
argument-hint: (no arguments needed)
---

# Init — New Project

**Role: Project Designer**
**Use on projects with no code yet. For existing codebases, use `/setup`.**

Interviews the developer, recommends the right platform and architecture, and
writes `CLAUDE.md` + `ARCHITECTURE.md` as a blueprint. All lifecycle skills
read these files from the first CR onward.

---

## Step 1: Check for existing code

Check if any of these exist: `src/`, `lib/`, `app/`, `package.json`, `pyproject.toml`, `pubspec.yaml`.

If any exist:
> "This directory already has code. Use `/setup` to configure an existing project instead."

Stop.

If `CLAUDE.md` exists with `Praxis Platform:`:
> "This project is already configured. Use `/setup` to regenerate the architecture snapshot."

Stop.

---

## Step 2: Size discovery question

Ask one question first to calibrate the depth of the interview:

> "What are you building? Give me a one-sentence description."

From the answer, estimate scope:
- **Tiny**: CRUD app, personal tool, small internal utility, single domain
- **Medium**: Multi-feature product, 2-5 domains, some external integrations
- **Large**: Multi-tenant SaaS, complex workflows, 5+ integrations, real-time features, or team of 3+

---

## Step 3: Proportional design interview

Ask questions one at a time and wait for each answer.

**Tiny (2 more questions after Step 2):**

> Q2: "Who uses it and how do they access it?
> (e.g. just me via CLI, a small team via web, mobile users)"

> Q3: "Any external services it needs to talk to?
> (e.g. Stripe, Firebase, an API — or none)"

**Medium (4 more questions after Step 2):**

> Q2: "Who are the user types and how do they access the system?
> (e.g. web app for shippers, mobile app for drivers, admin panel)"

> Q3: "What are the main business concepts this system will manage?
> (e.g. orders, shipments, users, payments — list them)"

> Q4: "What external services will it integrate with, and what for?"

> Q5: "Will it serve multiple companies or organisations from one deployment
> (multi-tenant), or is it single-tenant?"

**Large (6 more questions after Step 2):**

> Q2: "Who are the user types and how do they access the system?"

> Q3: "What are the main business domains?
> (list them — each domain = a distinct bounded area of responsibility)"

> Q4: "What external services will it integrate with, and what for?
> (list all — auth, payments, messaging, GPS, storage, etc.)"

> Q5: "Multi-tenant or single-tenant? If multi-tenant, how strict is isolation?
> (e.g. shared DB with RLS, separate DBs per tenant, separate deployments)"

> Q6: "Expected scale: users, data volume, traffic patterns?
> Any real-time or high-frequency components (GPS, live tracking, webhooks)?"

> Q7: "Team size and any hard constraints?
> (e.g. must use GCP, existing Firebase project, regulatory requirements)"

---

## Step 4: Platform and architecture recommendation

Based on the answers, recommend platform and architecture.

**Platform selection guide (examples — not exhaustive):**

| Signal | Recommendation |
|--------|---------------|
| Python team, complex domain logic, many integrations | `python-fastapi` or `django` |
| TypeScript team, enterprise patterns, relational DB | `nestjs` |
| Web frontend, React, server-side rendering | `nextjs` |
| Mobile app, iOS + Android | `flutter` or `react-native` |
| High concurrency, systems programming | `go` or `rust` |
| Rapid prototyping, convention over config | `rails` or `laravel` |
| JVM ecosystem, existing Java/Kotlin team | `spring-boot` |
| Full-stack | pick backend + pick frontend (two separate `/init` runs) |

Use whatever fits the team, constraints, and use case. The Praxis lifecycle works
with any stack.

**Architecture complexity guide:**

| Signal | Architecture |
|--------|-------------|
| Tiny, ≤2 domains, no multi-tenancy | Layered — simple service + repository |
| Medium, 3-7 domains | Hexagonal — ports + adapters, clear boundaries |
| Large, multi-tenant, many integrations, custom IoC | Hexagonal + YAML-driven IoC container (EIL pattern) |
| Real-time / event-heavy | Add async event bus (NEL pattern) |

Present the recommendation:

> "Based on what you described, here's my recommendation:
>
> **Platform:** `[platform]`
> **Architecture:** [layered | hexagonal | hexagonal + IoC container]
> **Multi-tenancy:** [RLS + app-level filtering | none]
> **Async strategy:** [sync only | in-process event bus | Cloud Tasks]
>
> **Why:**
> - [Key reason 1]
> - [Key reason 2]
> - [Any trade-off worth naming]
>
> Does this direction work, or do you want to change anything?"

Wait for confirmation. Adjust if needed. Set `platform` from confirmed choice.

---

## Step 5: Ask domain and gates

Ask these two questions, one at a time:

> **Q — Domain:** "What kind of work will happen in this project primarily?
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
> (e.g. 'disable plan' or 'all on')"

---

## Step 6: Write CLAUDE.md

Append to `CLAUDE.md` (create if missing):

For `software` domain — derive all values from the recommended platform:
```
## Praxis Configuration

Praxis Platform:     <platform>
Praxis Domain:       software
Praxis Gates:        spec=on, plan=on, review=on, lessons=on
Praxis TestCommand:  <standard test command for this platform>
Praxis TestRunner:   <runner name, e.g. pytest, jest, go test>
Praxis Language:     <language, e.g. python, typescript, go>
Praxis SourceRoot:   <standard source root for this platform, e.g. src/>
Praxis FileExt:      <file extension, e.g. *.py, *.ts, *.go>
Praxis IsolationKey: <none, or the isolation field if multi-tenant was confirmed>
```

For non-software domains:
```
## Praxis Configuration

Praxis Domain:  <content|research|strategy|general>
Praxis Gates:   spec=on, plan=on, review=on, lessons=on
```

Adjust `Praxis Gates` based on the developer's answer. Derive platform-specific values from the confirmed stack — do not ask about them individually.

---

## Step 7: Write ARCHITECTURE.md blueprint

Write `ARCHITECTURE.md` at the project root. Mark all sections as planned — this
is a blueprint, not a snapshot of existing code.

```markdown
# Project Architecture Blueprint
<!-- Mode: greenfield — no code exists yet -->
<!-- Generated by /init on [date]. Update as code is written. -->
<!-- All Praxis lifecycle skills read this file instead of scanning the codebase. -->

## Platform
[platform]

## Project Size
[Tiny | Medium | Large]

## What This Project Does
[1-2 sentence description from interview]

## User Types
[from interview — who uses the system and how]

## Planned Directory Structure
[standard structure for the platform — mark as "(planned)"]
[Use the layout from the platform's stack reference]

## Planned Domains / Feature Areas
[from interview — each domain with one-line responsibility]

## External Integrations
[from interview — each service + what it's used for]
[if none: "None planned"]

## Environment Configuration Strategy
[from recommendation — env vars + BaseSettings | ConfigModule | YAML-driven IoC]
[if YAML-driven IoC: note that eil.local.yaml / eil.prod.yaml pattern applies]

## Multi-Tenancy
[from recommendation — isolation mechanism]
[if not multi-tenant: "Single tenant"]

## Async Strategy
[sync only | in-process event bus | Cloud Tasks + event bus]

## Architecture Approach
[layered | hexagonal | hexagonal + IoC container]
[one paragraph explaining why this fits the project]

## Established Patterns
(to be filled as first CRs are implemented)

## Complexity Hotspots
(to be filled as implementation progresses)

## Test Strategy
[agreed approach from platform stack reference]
[e.g. "Unit tests with FakeRepository pattern, integration tests against real DB in CI"]
```

---

## Step 8: Install the enforce-spec-first hook

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

## Step 9: Confirm

> **Praxis initialised — [platform] — [Tiny | Medium | Large] project.**
>
> - Platform recorded in `CLAUDE.md`
> - Domain: `[domain]`
> - Gates: `[active gate list]`
> - Architecture blueprint written to `ARCHITECTURE.md`
>   - [N] planned domains documented
>   - [N] external integrations planned
>   - [architecture approach] architecture agreed
> - Spec-first hook installed at `.git/hooks/pre-commit`
>
> `ARCHITECTURE.md` is a blueprint — update it as code is written and structure
> becomes real. Re-run `/setup` once the codebase has significant code to get a
> scan-based snapshot.
>
> Next step: `/triage <describe the first feature to build>`

---

## Relationship between /init and /setup

- `/init` writes a **blueprint** based on design intent — no code to scan.
- `/setup` writes a **snapshot** based on actual code — scan-first, questions fill gaps.
- After a project initialised with `/init` grows significantly, re-run `/setup`
  to replace the blueprint with a real snapshot.
