# Spec Quality Rules

## Purpose

A spec is the contract between intent and implementation. A poor spec wastes engineering effort. These rules define what makes a spec ready to be reviewed and approved.

---

## Required sections

Every spec must contain all of the following. A section may be brief if the CR is simple — but it may not be absent.

| Section | What it must cover |
|---|---|
| Problem statement | What is broken or missing, for whom, and why it matters. Explicit out-of-scope subsection. |
| Bounded context | Which domain, which entities owned, which events published, which contexts depended upon |
| Inbound ports | Every operation exposed. Auth required. Roles permitted. Read-RBAC per role. |
| Outbound ports | Every external dependency. Method signatures with the project's isolation key (from `Praxis IsolationKey`) as first param if applicable. Bridge/Gateway flag. |
| Adapter contracts | Concrete implementations: endpoints, schemas, operation ordering for multi-step commands |
| Data isolation strategy | How the isolation key (`Praxis IsolationKey`) is resolved, scoped, and validated. Mark N/A if `Praxis IsolationKey: none`. |
| Security defaults | Rate limit fallback policy, JWT expiry, read-RBAC summary, operation ordering — no TBD |
| Acceptance criteria | GIVEN/WHEN/THEN format. Testable. Specific. No vague language. |
| Error scenarios | Auth failures (5 mandatory rows). Domain errors with domain exception names, not HTTP codes. |
| Side effects | Domain events triggered, consumers, sync/async, failure policy |
| Non-functional requirements | Latency targets, throughput, data volume, rate limits, idempotency TTL |
| Contract Impact | CONDITIONAL. If any public contract surface is modified: document the
                   surfaces, breaking yes/no, known dependents, and the compatibility decision.
                   If breaking: consumer CRs must be created and listed. Mark `N/A` with
                   one-sentence justification only when no contract surface is touched. |

---

## Acceptance criteria rules

Every acceptance criterion must be:

- **Specific** — no vague terms: "appropriate", "as needed", "handle gracefully", "relevant data"
- **Measurable** — has a clear pass/fail condition
- **Testable** — can be verified with a deterministic automated test
- **GIVEN/WHEN/THEN format** — precondition, action, and expected outcome are all explicit

Bad: "The system should handle errors gracefully."

Good: "GIVEN a payment attempt fails with a gateway timeout, WHEN the user retries, THEN the system checks idempotency and returns the original response if the first attempt was recorded."

---

## What blocks a spec from being approved

The following are BLOCKER conditions:

- Any required section is absent
- Any `BUSINESS DECISION REQUIRED` marker remains unfilled
- Any acceptance criterion that cannot be verified with a deterministic test
- Any vague language that can be interpreted more than one way
- Data isolation not addressed for any data access path (when `Praxis IsolationKey` is set)
- Auth requirement undefined for any write endpoint
- Error scenarios missing the 5 mandatory auth failure rows
- Security defaults section has any blank or "TBD" field
- Port interface defined with adapter types in the method signature
- A public contract surface is modified AND no `## Contract Impact` section is present
- `## Contract Impact` records a breaking change AND no consumer CRs have been created
- `## Contract Impact` contains a `BUSINESS DECISION REQUIRED` marker — compatibility
  decision not yet recorded

---

## Annotation conventions

Authors use these markers to signal review-time state:

| Annotation | Meaning |
|---|---|
| `(default)` | Pre-decided technical default, applied automatically — do not change without documented reason |
| `(inferred — verify)` | Derived from context; needs explicit confirmation |
| `BUSINESS DECISION REQUIRED` | Only the human can fill this in; blocks approval |

A spec with any `BUSINESS DECISION REQUIRED` marker remaining may not be approved.

---

## Proportionality

Spec depth is proportional to CR complexity:

| CR type | Expected depth |
|---|---|
| New module or domain concept | All sections fully populated |
| New endpoint on existing pattern | Problem statement, ports, adapter contracts, ACs, errors |
| Security or tenant isolation fix | Problem statement, tenant isolation, ACs, error scenarios |
| Refactor, structural improvement | Problem statement, bounded context, ACs |
| Incident follow-up | Problem statement, root cause, ACs, errors |

A section that is genuinely not applicable should be marked `N/A — not applicable to this CR type` with a one-sentence justification. It must not be blank.

---

## Spec quality checklist

Before declaring a spec ready for review:

- [ ] No placeholder text (no TBD, TODO, fill in later)
- [ ] No ambiguous language
- [ ] All ports defined as interfaces, not implementations
- [ ] Data isolation addressed for every data access path (when `Praxis IsolationKey` is set)
- [ ] Every AC follows GIVEN/WHEN/THEN
- [ ] Every error scenario has an explicit behavior defined
- [ ] Side effects are domain events — not direct service calls
- [ ] Security defaults section fully populated
- [ ] Auth failures section present with all 5 rows
- [ ] Read-RBAC defined for every port that returns data
- [ ] Operation ordering defined for every multi-step command
- [ ] Contract Impact section present (populated or explicitly N/A with justification)
- [ ] If breaking change: consumer CRs created and listed with CR-IDs
