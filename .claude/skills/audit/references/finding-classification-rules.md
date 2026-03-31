# Finding Classification Rules

## Purpose

These rules govern how a reviewer assigns finding class and severity, and how findings are grouped and presented in a review report. Consistent classification is what makes review reports actionable and comparable across stages and reviewers.

---

## Classification process

For every potential issue found during review, apply this sequence:

1. **Is it a real problem?** If the code or spec is correct, do not raise it as a finding. Hypothetical issues and stylistic preferences are not findings.

2. **What is the finding class?** Assign the single most specific class (see below).

3. **What is the severity?** Assign severity based on impact and exploitability, not on aesthetics (see `review-severity-model.md`).

4. **Is there a concrete location?** If you cannot cite an exact file + line or spec section, do not raise the finding until you can.

5. **Is the remediation actionable?** If you cannot state a concrete fix, do not raise the finding until you can.

---

## Finding class definitions and assignment rules

### `architecture`

Assign when: the finding is about the structure of the system — how layers, ports, or adapters are arranged and how they depend on each other.

Includes:
- Dependency direction violations (domain importing adapters, application importing adapters)
- Port interface in wrong location
- Adapter implementing logic that belongs in domain
- Pattern violations (missing Bridge, direct side effect instead of NEL, repository without port)
- Missing architectural structure that the change requires (e.g., missing port for a new external dependency)

Does not include: implementation quality issues within a correctly placed component.

### `domain`

Assign when: the finding is about the correctness or completeness of business rules, invariants, or domain model design.

Includes:
- Business rule missing from a domain model
- Invariant not enforced (entity can reach an invalid state)
- Acceptance criterion that is untestable or ambiguous
- Domain concept misnamed or misrepresented
- Business logic in the wrong place (leaked into application or adapter)

Does not include: architectural structure issues — those are `architecture`.

### `implementation`

Assign when: the finding is about the quality, correctness, or completeness of the implementation within an otherwise correctly placed component.

Includes:
- Error case not handled
- Incorrect algorithm or calculation
- Missing null/empty check
- Disproportionate complexity for the task
- Inconsistency between spec acceptance criteria and actual implementation

Does not include: anything that should be `architecture`, `security`, or `testing`.

### `security`

Assign when: the finding creates or exposes a security risk.

Includes:
- Data isolation gap (query without isolation key, or cross-context access path)
- Authentication check missing
- Authorisation check missing or insufficient
- Input not validated at adapter boundary
- Secret or credential in code
- Data exposure (returning more data than the caller is authorised to see)
- Injection risk (SQL, command, path traversal)

Note: a missing isolation key filter is always classified as `security`, not `architecture`, because the risk is data exposure, not structural.

### `testing`

Assign when: the finding is about test coverage or test quality.

Includes:
- Critical path not tested
- Acceptance criterion with no corresponding test
- Missing cross-tenant isolation test on a data access path
- Error scenario not tested
- Test that does not actually fail when the code it tests is broken (vacuous test)

Does not include: test quality issues that are purely stylistic.

### `platform`

Assign when: the finding is about deployment, infrastructure, operations, or runtime behaviour.

Includes:
- Migration not reversible
- Missing rollback path
- Change that requires manual deployment step not documented
- Observable failure mode not logged or instrumented
- Resource leak (connection, file handle, memory) under load
- Configuration change not reflected in deployment manifests

---

## When a finding spans multiple classes

If a finding genuinely involves more than one class, assign the class that reflects the primary risk. For example:

- A missing tenant filter is `security` (not `architecture`) because the primary risk is data exposure.
- A domain model that calls a repository directly is `architecture` (not `domain`) because the primary problem is structural.
- A missing test for a security-critical path is `testing` (not `security`), unless the absence of the test masks an already-present security flaw.

---

## What is not a finding

Do not raise as a finding:
- Stylistic preferences not grounded in the project doctrine
- Hypothetical risks with no realistic attack or failure path
- Issues already identified and explicitly deferred in the spec as non-scope
- General improvement ideas unrelated to the change under review
- Observations without a concrete remediation

These may be noted as informal comments but must not appear in the formal findings list.
