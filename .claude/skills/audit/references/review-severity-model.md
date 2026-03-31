# Review Severity Model

All reviews in this system use one shared severity model. Severity determines the gate effect — whether a finding blocks advancement or is recorded as advisory.

---

## Severity levels

| Severity | Gate effect | Disposition | Meaning |
|---|---|---|---|
| `CRITICAL` | Blocker | Must fix before advancing | Exploitable now, or causes data loss, breach, or system failure |
| `HIGH` | Blocker | Must fix before advancing | Likely exploitable with effort, or architectural violation that propagates |
| `MEDIUM` | Non-blocker | Should fix | Defence-in-depth gap, or code quality issue with meaningful risk |
| `LOW` | Non-blocker | Advisory | Best practice deviation with low risk; worth tracking but not blocking |

A `CRITICAL` security finding always blocks, with no exception and no business override.

A `HIGH` architecture finding always blocks. The architecture is either sound or it is not — there is no "acceptable violation" category.

---

## Finding classes

Every finding belongs to exactly one class:

| Class | What it covers |
|---|---|
| `architecture` | Layer boundary violations, dependency direction, port/adapter misuse, pattern violations |
| `domain` | Missing business rules, incorrect invariants, ambiguous or untestable acceptance criteria |
| `implementation` | Code quality, error handling gaps, missing edge cases, disproportionate complexity |
| `security` | Auth gaps, tenant isolation failures, injection risks, data exposure, secrets handling |
| `testing` | Inadequate coverage, missing critical-path tests, untested error scenarios |
| `platform` | Infrastructure, deployment, migration, observability, operational risk |

---

## Required finding structure

Every finding must include all of the following:

| Field | Requirement |
|---|---|
| **Severity** | One of: CRITICAL / HIGH / MEDIUM / LOW |
| **Class** | One of the six finding classes |
| **Location** | Exact file path + line number (for code), or spec section (for spec review) |
| **Statement** | One-sentence description of what is wrong |
| **Rationale** | Why this is a problem — the rule it violates or the risk it creates |
| **Remediation** | Concrete, actionable fix — not "consider improving this" |

A finding without a location is not a finding. A finding without a concrete remediation is not actionable.

---

## Verdict

Every review produces a single verdict:

- `PASS` — no BLOCKER findings, or all BLOCKERs resolved
- `BLOCKED` — one or more BLOCKER findings remain unresolved

A `BLOCKED` verdict prevents the CR from advancing to the next stage.

Non-blocking findings (MEDIUM / LOW) are recorded as advisories in the review report. They do not affect the verdict but must appear in the Closure artifact if unresolved at close.

---

## Severity assignment guidance

When assigning severity, reason from impact and exploitability, not from code aesthetics.

**CRITICAL examples:**
- Cross-tenant data access possible without authentication
- SQL injection via unsanitised input
- Hardcoded secret in committed code
- Domain layer directly calling a database without port abstraction (complete architecture collapse)

**HIGH examples:**
- Missing tenant_uid filter on a repository method
- Application layer importing from adapters (architectural violation)
- Authentication check missing on a write endpoint
- Domain event not published for a state-changing operation

**MEDIUM examples:**
- Error case not handled (returns 500 instead of meaningful error)
- Missing index on a frequently-queried column
- Query method returns more data than the use case requires
- Test coverage missing for an edge case

**LOW examples:**
- Variable naming inconsistent with project conventions
- Missing docstring on a public method
- Unused import
- Log message missing context fields
