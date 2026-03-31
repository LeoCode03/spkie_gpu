# Backlog Persistence Rules

## Source of truth

The `.cr.md` file owns canonical CR state. `BACKLOG.md` is a read-optimised projection of open CRs, derived from the `.cr.md` files present in the working tree.

`BACKLOG.md` is reconstructible at any time by scanning all `specs/cr/*.cr.md` files currently present in the working tree and rebuilding the table from their fields.

## What survives in main

`main` carries:
- `specs/cr/BACKLOG.md`
- all open CR artifact files (`*.cr.md`, `*.spec.md`, `*.plan.md`)
- all implementation artifacts (`src/`, `tests/`, docs)

`main` does not carry:
- any artifact file for a closed CR
- archive folders or gitignored evidence directories

Closed CR evidence is preserved in git history only. No archive folder is needed.

## BACKLOG.md format

File path: `specs/cr/BACKLOG.md`

~~~markdown
# CR Backlog

<!-- Auto-managed by Praxis lifecycle skills. Do not edit by hand. -->
<!-- Source of truth: open specs/cr/<cr-id>.cr.md files in the working tree. -->

| CR-ID | Type | Sev | Status | Summary | Updated |
|-------|------|-----|--------|---------|---------|
~~~

Rules:
- One row per open CR
- Rows sorted by CR-ID ascending (chronological by construction)
- No row for closed CRs — closed evidence lives in git history
- No archive section

## Commit convention

```
chore(cr): <cr-id> → <state> — <one-line summary>
chore(cr): <cr-id> — cleanup, artifacts removed from working tree
```

Files staged: `specs/cr/` only. Never stage `src/`, `tests/`, or unrelated files in a CR process commit.

## Push policy

Always attempt `git push` after a CR process commit. If push fails, warn and continue. Push failure never blocks the lifecycle.

```bash
git push || echo "[warn] Push failed — commit is local. Push manually when ready."
```

## The two-commit close sequence

Closing a CR requires exactly two commits to preserve closure evidence in git history while delivering a clean working tree to `main`.

**Commit A — closure evidence**
Write all closure artifacts, update `.cr.md` state to CLOSED, remove the CR from BACKLOG.md, then commit and push. After this commit, git history contains the full closure record.

**Commit B — working tree cleanup**
Remove all `specs/cr/` artifact files for this CR using `git rm --ignore-unmatch`, then commit and push. After this commit, the working tree is clean. No CR artifact files remain in `specs/cr/` for this CR.

When the branch merges to `main`, `main` receives the clean tree and the evidence is preserved in git history only.

## Rollout — Phase 1

`intake` and `close` implement backlog persistence. Additionally, `spec` creates consumer CRs for breaking contract changes (Exception A), and `close` creates late-detected consumer CRs as an anomaly path (Exception B).

All other mid-lifecycle writes (`plan`, `build`, `review`) do not yet produce CR process commits. Phase 2 will extend persistence to those stages.

**Exception A — spec creates consumer CRs:**
When the spec stage identifies a breaking contract change, it creates one consumer CR per
dependent system. Each consumer CR follows the identical intake write protocol:
1. Write `specs/cr/<consumer-cr-id>.cr.md` using the consumer CR format in
   `contract-impact-rules.md`
2. Add one row to `specs/cr/BACKLOG.md`
3. Commit: `chore(cr): <consumer-cr-id> → OPEN — <dependent-system>: adapt to breaking change`
4. Push with the standard push policy

**Exception B — close creates late-detected consumer CRs (anomaly path):**
If close Phase 3 discovers that consumer CRs that should have been created at spec time are
missing, it creates them using the same protocol as Exception A. The closure artifact must
note: "Consumer CR <cr-id> created at close time — late detection; contract impact was not
fully resolved at spec." This flags the process gap without blocking closure.

Consumer CRs are independent CRs from the moment of creation. They follow the full lifecycle
on their own timeline.

## BACKLOG reconstruction

To reconstruct `BACKLOG.md` from scratch, scan all `specs/cr/*.cr.md` files present in the working tree. For each file, extract the CR-ID, Type, Severity, Status, and Summary fields and add one row. The result is the complete set of open CRs.
