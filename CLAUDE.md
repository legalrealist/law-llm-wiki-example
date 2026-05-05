# Law School Wiki — Schema & Workflows

This is the schema file for the law school notes wiki. It defines the directory layout, page conventions, and workflows that Claude follows to maintain this wiki across sessions. Read this file at the start of every session.

---

## Directory Layout

```
llm-wiki/
├── CLAUDE.md                  ← this file (schema & instructions)
├── raw/                       ← IMMUTABLE source documents — read only, never modify
│   ├── extracted/             ← pre-extracted .txt versions of all notes (READ HERE FIRST)
│   ├── articles/              ← articles, law review pieces
│   ├── papers/                ← PDFs (cases, statutes, supplements)
│   ├── notes/                 ← course outlines and class notes (.docx, .pdf)
│   └── assets/                ← images and attachments
└── wiki/                      ← LLM-owned — Claude writes and maintains everything here
    ├── index.md               ← master catalog of all wiki pages (update on every ingest)
    ├── log.md                 ← append-only chronological record of operations
    ├── overview.md            ← evolving synthesis across all subjects
    ├── courses/               ← one page per course (Contracts I, Torts, etc.)
    ├── doctrines/             ← one page per legal doctrine or rule
    ├── cases/                 ← one page per important case
    └── statutes/              ← one page per statute, rule, or regulation
```

**Rule**: Never modify anything under `raw/`. All wiki content lives under `wiki/`.

---

## Page Conventions

### Frontmatter (YAML, Dataview-compatible)

Every wiki page must start with frontmatter:

```yaml
---
type: course | doctrine | case | statute | overview
tags: [tag1, tag2]
sources: 0
updated: YYYY-MM-DD
---
```

- `type`: one of the five categories above
- `tags`: subject area keywords (e.g. `[contracts, offer-acceptance]`, `[torts, negligence]`)
- `sources`: count of raw sources that have contributed to this page
- `updated`: date this page was last modified (ISO format)

### Cross-references

Always use Obsidian wikilinks: `[[Page Name]]`. File names should match the page title exactly.

### Filenames

Use the page's full title exactly, with spaces and natural capitalization: `Consideration.md`, `Hadley v Baxendale.md`, `Contracts I.md`. The filename must match the H1 heading, which must match the `[[wikilink]]` used to reference the page. This is what makes Obsidian backlinks work.

### Course Pages

Each course page should include:
- Course info (professor, semester, year)
- High-level outline of topics covered
- Key doctrines taught (wikilinked to doctrine pages)
- Key cases covered (wikilinked to case pages)
- Exam approach / checklist if present in the notes

### Doctrine Pages

Each doctrine page should include:
- Definition / rule statement
- Elements (numbered list)
- Exceptions and edge cases
- Policy rationale
- Key cases illustrating the doctrine (wikilinked)
- Which courses cover this (wikilinked)

### Case Pages

Each case page should include:
- Citation and court
- Facts (brief)
- Issue
- Holding
- Rule / doctrine it stands for
- Significance / why it matters
- Which courses reference it (wikilinked)

---

## Ingest Workflow

When the user asks Claude to ingest a source from `raw/`:

1. **Read** the source. **Always check `raw/extracted/` first** — pre-extracted `.txt` versions of every source file are stored there and are much faster to read with the Read tool. Only fall back to python-docx or the PDF reader if no `.txt` counterpart exists. Write `ingest-start` to `wiki/log.md` before doing anything else.
2. **Discuss** key takeaways with the user if they want — what subjects are covered, what doctrines are central.
3. **Write or update `wiki/courses/<slug>.md`** — a course summary page.
4. **Update doctrine pages** — for each significant doctrine in the notes: open `wiki/doctrines/<slug>.md` (create if missing), integrate definitions, elements, exceptions, and cases.
5. **Update case pages** — for significant cases cited: open `wiki/cases/<slug>.md` (create if missing), fill in facts/holding/rule.
6. **Update `wiki/overview.md`** if the source adds a new subject area or meaningfully changes the synthesis.
7. **Update `wiki/index.md`** — add the new course page and any newly created doctrine/case pages.
8. **Write `ingest-complete` to `wiki/log.md`** — include the `Source:` path and list of all pages updated.

### Reading sources — order of preference

1. **`raw/extracted/<filename>.txt`** — use the Read tool directly. Fast and preferred.
2. **`raw/notes/<filename>.pdf`** — use the Read tool with `pages` parameter if no `.txt` exists.
3. **`raw/notes/<filename>.docx`** — use python-docx only as a last resort when no `.txt` or readable PDF exists:

```python
from docx import Document
doc = Document('/Users/hao/Claude/llm-wiki/raw/notes/filename.docx')
text = '\n'.join([p.text for p in doc.paragraphs])
print(text)
```

The `raw/extracted/` directory mirrors `raw/notes/` with the same base filenames (`.docx` → `.txt`, `.pdf` → `.txt`).

---

## Query Workflow

When the user asks a question:

1. Read `wiki/index.md` to identify relevant pages.
2. Read those pages and follow wikilinks as needed.
3. Synthesize an answer with citations to wiki pages.
4. **If the answer is substantive** (e.g. a doctrine comparison, an exam issue-spotter), offer to file it as a new wiki page.

---

## Lint Workflow

Periodically, or when asked:

1. **Orphan pages** — pages with no inbound links.
2. **Missing pages** — wikilinks pointing to pages that don't exist yet.
3. **Contradictions** — conflicting rule statements across courses (flag with `> [!warning]`).
4. **Incomplete pages** — doctrine or case pages missing key sections.
5. **Missing cross-references** — pages that should link to each other but don't.

---

## Index Format

`wiki/index.md` uses per-section markdown tables:

```markdown
| Page | Summary | Updated |
|------|---------|---------|
| [[Page Name]] | One-line summary | YYYY-MM-DD |
```

Sections: Overview, Courses, Doctrines, Cases, Statutes.

---

## Log Format

All log entries use the format:

```
## [YYYY-MM-DD] <operation> | <title>
```

Operations: `ingest-start`, `ingest-complete`, `query`, `lint`, `update`, `init`.

### Ingest entries (two entries per source)

Write `ingest-start` at the **beginning** of every ingest — before writing any wiki pages:

```
## [YYYY-MM-DD HH:MM] ingest-start | Contracts I (FL15)
Source: raw/extracted/Contracts_I_FL15.txt
```

Write `ingest-complete` at the **end**, after all pages are written:

```
## [YYYY-MM-DD HH:MM] ingest-complete | Contracts I (FL15)
Source: raw/extracted/Contracts_I_FL15.txt
Pages updated: [[Contracts I]], [[Consideration]], [[Hadley v Baxendale]], [[Promissory Estoppel]]
```

The `Source:` line must be the exact relative path from the project root. The script uses `ingest-complete` + `Source:` to detect which files have been processed. If a session ends before writing `ingest-complete`, the source will appear as in-progress on the next run.

Entries are append-only — never delete or edit past entries.

---

## Notes

- **Prefer updating existing doctrine pages** over creating new ones. Many courses cover the same doctrines — build up one authoritative page per doctrine rather than duplicating across courses.
- **Exam checklists are gold.** If a source has an issue-spotting checklist or exam approach, extract it prominently into the course page and the relevant doctrine pages.
- **Cross-course connections matter.** When a doctrine appears in multiple courses (e.g. consideration in Contracts I and II), note the cross-reference on the doctrine page.
