# Lessons Learned Rules

## Purpose

Capture non-obvious knowledge from CR closures so it is available to future CR work.
This is not a diary — it is a curated record of things that would cost time to rediscover.

---

## The file

`specs/lessons-learned.md` in the consumer project.

- Permanent and append-only. Entries are never removed.
- Created on first write. If it does not exist, create it with this header:

```markdown
# Lessons Learned

Accumulated from CR closures. Each entry cites the originating CR and is permanent.
```

---

## Entry format

```markdown
## LL-01
- **Source:** CR-<cr-id>
- **Date:** <YYYY-MM-DD>
- **Rule:** <one actionable sentence>
- **Why it matters:** <what made this non-obvious, or why it will recur>
```

IDs are sequential integers, zero-padded to two digits (LL-01, LL-02, …).
Read the file to find the last ID before writing a new entry.

---

## Write — at CR close

After verifying acceptance criteria, before producing the closure artifact:

1. Review the entire CR — spec, build summary, review findings, any notes.
2. For each candidate lesson, apply the quality gate:

   > **Keep if:** the lesson is non-obvious to a competent engineer in this domain,
   > OR it is likely to recur in future CRs.
   >
   > **Discard if:** a competent engineer would find it quickly, or it is generic
   > good practice ("write tests", "communicate early"). These are not lessons.

3. Write survivors to `specs/lessons-learned.md` as new LL-XX entries.

4. If a lesson looks like a **missing process rule or convention** — not a knowledge
   item but a gap in how the team works — surface it explicitly to the human:
   > "This may warrant a doctrine update — consider `/triage` if you agree."
   Do NOT modify doctrine or create CRs autonomously.

---

## Read — at CR start

At the start of any CR phase (intake, spec, plan, build, review):

1. Check if `specs/lessons-learned.md` exists. If not, skip.
2. Read the file and identify entries relevant to this CR by keyword match
   against the CR title, domain, and affected components.
3. Surface relevant entries before work begins:
   > "Relevant lessons from prior CRs: [LL-XX] ..."

Do not surface entries with no connection to the current CR. When in doubt, include.

---

## What makes a good lesson

**Keep:**
- A non-obvious infrastructure or platform behaviour (e.g. Cloudflare does not serve
  binary files without specific cache rules)
- An implementation gotcha that cost significant discovery time (e.g. constructor
  positional args that silently break test fixtures)
- A domain-specific constraint that is not in any documentation

**Discard:**
- Anything findable in official docs within a few minutes
- Generic engineering principles
- One-off incidents unlikely to repeat
