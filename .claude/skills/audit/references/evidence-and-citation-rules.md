# Evidence and Citation Rules

## Purpose

Review findings without evidence are opinions. Evidence and citation rules ensure that every finding can be independently verified, disputed, or acted upon without ambiguity.

---

## The evidence requirement

Every BLOCKER finding (CRITICAL or HIGH severity) must include:

1. **Exact location** — file path + line number, or spec section identifier
2. **The specific code or text** — a direct quote or snippet of the problematic content
3. **The rule violated** — citation of the specific principle, doctrine file, or pattern it contradicts
4. **The risk** — what happens if this is not fixed
5. **Concrete remediation** — specific code change, design change, or spec revision required

Non-blocking findings (MEDIUM or LOW) must include at minimum: location, statement of the problem, and remediation. The direct quote and rule citation are strongly recommended but not required for non-blockers.

---

## Citation format

When citing a violation of project doctrine, reference the specific rule:

```
Violation: boundary-rules.md — "Domain imports from adapters"
Location: src/domain/services/user_service.py, line 4
Code: from adapters.outbound.persistence import PostgresUserRepository
Remediation: Define a UserRepository port in domain/ports/outbound/user_repository.py
             and inject it via the constructor. Remove the direct import.
```

When citing a spec deficiency:

```
Violation: artifact-contracts.md — Acceptance criteria must be testable and unambiguous
Location: specs/cr/260315-142300.spec.md, Section: Acceptance Criteria, AC-3
Text: "The system should handle errors gracefully"
Remediation: Replace with: "When payment processing fails, the system returns HTTP 422
             with error code PAYMENT_FAILED and the order remains in PENDING state."
```

---

## What counts as sufficient evidence

**Sufficient:**
- File path + line number + quoted code
- Spec section + quoted text
- Diagram or structure reference with specific node identified

**Insufficient:**
- "The code has architecture violations" (no location)
- "Tests are missing" (which tests, which paths)
- "This could be improved" (not a finding)
- "Consider using X pattern" (no violation identified)

---

## Location format

For code findings:
```
src/domain/services/user_service.py:47
```

For spec findings:
```
specs/cr/260315-142300.spec.md §6 Acceptance Criteria AC-2
```

For plan findings:
```
specs/cr/plans/260315-142300.plan.md §3 Ordered Steps, Step 4
```

Always use the full path from the repository root, not a relative path.

---

## Disputed findings

If the implementor believes a finding is incorrect, they must respond with counter-evidence in the same format:

- Cite the rule they believe is satisfied
- Show the specific code or text that satisfies it
- Explain why the reviewer's location reference is not a violation

A finding is not resolved by disagreement alone. It is resolved when the counter-evidence demonstrates that the cited rule is not violated, or when the finding is corrected.

---

## Review report structure

A review report groups findings as follows:

```
## Verdict: PASS | BLOCKED

## BLOCKER findings
[Each finding with full evidence: location, code/text, rule, risk, remediation]

## Non-blocking findings
[Each finding with: location, statement, remediation]

## Advisories
[Optional observations that do not meet the bar for a formal finding]
```

Blockers are listed first, by severity (CRITICAL before HIGH). Non-blocking findings follow, by severity (MEDIUM before LOW). Advisories are last.

The verdict is `BLOCKED` if any BLOCKER findings remain unresolved. It is `PASS` otherwise. The verdict must appear at the top of the report, not at the end.
