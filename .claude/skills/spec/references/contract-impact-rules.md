# Contract Impact Rules

## What is a contract surface

A contract surface is any interface your system exposes that external consumers depend on.
Breaking a contract surface breaks those consumers.

| Surface type | What to look for |
|---|---|
| REST endpoint | Route/controller decorator + request/response schema |
| Domain event | Event class published to message bus or Pub/Sub |
| Shared port interface | Abstract class or interface used across bounded contexts |
| DB schema (exposed) | Model fields read by other services directly |

## How to detect contract surfaces from code

Scan for the following before marking Contract Impact as N/A:

Use `Praxis FileExt` and `Praxis SourceRoot` from CLAUDE.md to construct detection commands. Patterns vary by stack — adapt to the project's routing layer, schema definitions, event definitions, and port interfaces.

Common detection patterns:
```bash
# REST endpoints — search the inbound/routing layer
grep -rn "<routing_decorator_pattern>" $PRAXIS_SOURCE_ROOT --include="$PRAXIS_FILE_EXT"

# Request/response schemas — search inbound adapters
grep -rn "class.*Schema\|class.*Model\|class.*Dto\|class.*Request\|class.*Response" \
  $PRAXIS_SOURCE_ROOT --include="$PRAXIS_FILE_EXT"

# Domain events
grep -rn "class.*Event" $PRAXIS_SOURCE_ROOT --include="$PRAXIS_FILE_EXT"

# Port interfaces
grep -rn "class.*Port\|class.*Repository\|interface.*Repository\|trait.*Repository" \
  $PRAXIS_SOURCE_ROOT --include="$PRAXIS_FILE_EXT"
```

The routing decorator pattern depends on the framework. Read the stack reference to know what it looks like in this project.

## How to identify known dependents

Scan the codebase for consumers of the contract surface:

1. **REST endpoints**: search for the path string in other services' API client code
2. **Domain events**: search for the event class name in adapter event handlers and
   in any documented Pub/Sub subscriptions
3. **Port interfaces**: search for the port class name across all bounded contexts

If dependents cannot be determined from the codebase, ask once:
> "Are there external systems or teams that consume [contract surface]? If so, which?"

This is the only question about dependents that requires human input.

## How to classify a change: breaking or additive

**Rule: when in doubt, classify as breaking.**
A false positive fires a gate the human can dismiss in seconds.
A false negative ships a silent breaking change — the exact problem this process prevents.

**A change is breaking if any existing consumer would need to modify its code, configuration,
or schema to continue functioning correctly.**

Changes that appear additive but are breaking:
- Adding a required field to a request body
- Renaming an optional field (old name disappears)
- Changing a field type (e.g. string → int, nullable → non-nullable)
- Removing a deprecated field before its documented sunset date
- Changing an HTTP method or status code on an existing endpoint
- Narrowing a response schema (removing fields consumers may read)
- Changing an event name or Pub/Sub topic

Changes that are genuinely additive (not breaking):
- Adding an optional field to a response body
- Adding a new endpoint without modifying existing ones
- Adding a new optional query parameter
- Widening a response schema (adding new fields)
- Adding a new event type on a new topic

## Compatibility options

### Backwards compatible
The change does not break existing consumers. No consumer CRs needed.

Technical implementation (Claude decides — no human gate required):
- API versioning: introduce `/v2/` endpoint, keep `/v1/` with deprecation header
- Additive schema: add new field as optional, document deprecation of old field
- Dual-support period: defined in the spec Constraints section

### Breaking change
Requires a **Compatibility Decision** from the human (business question: is backwards
 compat required?). One consumer CR per dependent system must be created at spec time.

## Producer/consumer CR model

**Producer CR** — the CR that modifies the contract surface:
- Carries a `## Dependencies` section in its `.cr.md` listing all consumer CR-IDs spawned
- The spec artifact carries a `## Contract Impact` section with the full analysis
- The closure artifact carries a `## Dependencies` section (written in Commit A; preserved
  in git history after Commit B removes the file from the working tree)

**Consumer CR** — a CR created for each dependent system:
- Minimal CR item in `OPEN` state, created at spec time of the producer
- Carries `Triggered by: <producer-cr-id>` in its header table
- Follows the full CR lifecycle independently, on its own timeline
- Does not need to be CLOSED before the producer CR can be closed — only CREATED
- May itself be a producer: a CR may carry both `Triggered by` and `Produces`
  simultaneously if its adaptation work requires a further breaking change downstream

**Dependency field locations:**
- `Triggered by` — header table field in the consumer CR item (single value)
- `Produces` — body of `## Dependencies` section in the producer CR item (multi-value list)
Agents must look in different locations for each direction of the link.

## Consumer CR format

When creating a consumer CR, write `specs/cr/<new-cr-id>.cr.md`:

```markdown
# CR-<new-cr-id>

| Field        | Value |
|--------------|-------|
| CR-ID        | <new-cr-id> |
| Date         | <today> |
| Type         | feature |
| Severity     | Normal |
| Track        | Standard |
| Status       | OPEN |
| Triggered by | CR-<producer-cr-id> |
| Summary      | <dependent-system>: adapt to breaking change in <contract-surface> |

## Intent
Update <dependent-system> to consume the new <contract-surface> contract
introduced by CR-<producer-cr-id>.

## Assessment
Contract surface changed: <surface description>
Nature of breaking change: <what specifically changed>
Affected component in this system: <where the consumer code lives>
```

**Type, Severity, and Track defaults:** `feature / Normal / Standard`. Override when:
- Producer CR is `security` or `incident` → consumer CR inherits the same type and severity
- The breaking change has a hard deadline (coordinated release, compliance date) → raise
  severity to `High`
The consumer CR's own spec stage will re-assess classification as usual.

**CR-ID generation:** Use the incremental format `CR-NNNN`. Read `specs/cr/BACKLOG.md` to find the highest existing CR number, then increment. When creating multiple consumer CRs in a single session, increment sequentially (e.g. `CR-0043`, `CR-0044`).

Then add a row to `specs/cr/BACKLOG.md` and commit:
```bash
git add specs/cr/
git commit -m "chore(cr): <new-cr-id> → OPEN — <dependent-system>: adapt to breaking change"
git push || echo "[warn] Push failed — commit is local. Push manually when ready."
```

## Producer CR abandonment

If a producer CR is closed without implementing the breaking change (scope reduced, approach
changed to additive, or CR withdrawn), each of its consumer CRs must be closed with a
withdrawal note.

During close Phase 3, after verifying consumer CRs exist:
- Check whether the breaking change was actually delivered (present in build summary)
- If NOT delivered: for each consumer CR, perform a minimal withdrawal closure:
  - Update the `Status` field in the consumer CR's header table to `CLOSED`
  - Append a `## Closure` section to the consumer `.cr.md`:
    "Triggering change (CR-<producer-cr-id>) was withdrawn. This adaptation is no longer needed."
  - Remove the consumer CR row from `specs/cr/BACKLOG.md`
  - No `.close.md` file is needed — the `## Closure` section in the `.cr.md` is sufficient
  - Stage all changes: `git add specs/cr/`
  - Do NOT commit yet — these changes are committed in the producer's Phase 5 Commit A
    alongside the producer's own closure evidence
- The producer's closure artifact must note: "Consumer CRs [list] closed — triggering
  change was not delivered."

This is a legitimate path, not an error. The build may have found a backwards-compatible
approach after spec was written.

## When Contract Impact is N/A

Contract Impact may be marked `N/A` only when ALL of the following are true:
- The change modifies no REST endpoints, event schemas, or shared port interfaces
- The change modifies no response models or request schemas in the adapter layer
- The change is internal only (domain logic, private methods, test code, configuration)

If any contract surface is touched, Contract Impact must be populated — even if the conclusion
is "backwards compatible — no consumer CRs needed".
