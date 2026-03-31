# Implementation Planning Rules

## The role of Plan

Plan is the single authoritative stage for implementation strategy. Its job is to remove all implementation ambiguity before a line of code is written.

Build operates within what Plan defines. If Build encounters a situation the plan did not cover, it escalates — it does not improvise.

---

## What a good plan does

A good plan:

- Identifies the valid implementation approaches and states honest trade-offs between them
- Recommends one approach clearly, with a rationale the human can evaluate
- Sequences implementation in a layered order that respects architectural boundaries
- Makes every required structural decision explicit (which ports, which adapters, which commands, which events)
- Defines the test strategy so that QA is not improvised during Build
- Identifies migration and rollback implications before code is written
- Names the checkpoints where progress must be verified before continuing

A good plan does not:

- Leave structural decisions to Build
- Present options without recommending one
- Describe what the system will do without describing how it will be structured
- Omit test strategy
- Ignore migration or rollback implications when schema changes are involved

---

## Implementation approach selection

Plan must identify all valid approaches. "Valid" means technically sound and consistent with project doctrine.

For each approach, Plan states:
- What it involves structurally
- Its primary advantage
- Its primary trade-off or risk

Then Plan recommends one with a clear rationale. The human confirms or overrides. If the human overrides to a different approach, Plan generates the blueprint for the chosen approach.

When only one valid approach exists, Plan states it directly without manufacturing false alternatives.

---

## Blueprint structure

The implementation blueprint follows inside-out layer order:

```
1. Domain layer
   - New or modified entities, value objects, aggregates
   - New or modified port interfaces
   - New or modified domain services
   - New or modified domain events
   - New or modified domain exceptions

2. Application layer
   - New or modified commands (with handler structure)
   - New or modified queries (with handler structure)

3. Outbound adapters
   - Repository implementations
   - External API adapters and gateways

4. Inbound adapters
   - FastAPI router endpoints and schemas
   - Event handlers

5. Config / DI
   - New bindings in the DI container
   - New settings required
```

Every component named in the blueprint must be justified by the spec. Components not required by the spec must not appear in the blueprint.

---

## Test strategy

Plan defines the test strategy before implementation begins. Test skeletons are generated from acceptance criteria and placed in `tests/<cr-id>/`.

For every acceptance criterion in the spec, at least one test skeleton must exist.

Required test categories for any change that touches data access:
- Happy path (expected behaviour under normal conditions)
- Error path (expected behaviour when the operation fails)
- Tenant isolation (a second tenant must not access the first tenant's data through this code path)

Optional but expected for complex logic:
- Edge cases identified in the spec
- Boundary conditions on validated inputs

Test skeletons are designed to fail until Build implements the code. A skeleton that passes before Build runs is not a valid skeleton.

---

## Migration and rollback

If the plan involves schema changes, migrations, or data transformations, Plan must state:

- What migrations are required (forward)
- Whether the migration is reversible (and if not, why)
- What rollback looks like if the deployment fails after migration
- Whether the migration can run while the old code is still serving traffic (zero-downtime compatibility)

If migration details cannot be determined at Plan time, this is flagged as a risk in the plan — not silently deferred to Build.

---

## Risk re-assessment

After generating the blueprint, Plan re-assesses risk at the implementation level.

If a new HIGH or CRITICAL risk surfaces that was not present in the Intake or Spec assessment, Plan stops and presents it to the human before proceeding. The human decides whether to accept the risk, adjust scope, or return to Spec.

This is a conditional gate, not a mandatory stop. If no new risk surfaces, Plan completes without interruption.

---

## Proportionality

Plan depth is proportional to the change:

- A one-function bug fix may produce a one-page plan with three steps and two test skeletons
- A new subsystem may produce a ten-page plan with layered blueprints, migration notes, and twenty test skeletons

Proportionality is determined by what the change actually requires, not by what the developer requests. Plan decides the appropriate depth from the spec.
