#!/usr/bin/env python3
"""
wiki.py — maintenance toolkit for llm-wiki

Usage:
  python tools/wiki.py <command> [--dry-run] [--verbose]

Commands:
  ingest            Analyze source file(s), run maintenance pass, write ingest brief(s)
  lint              Find broken wikilinks, unlinked cases, redundant pages, naming violations, tagless pages
  link-cases        Add [[wikilinks]] to unlinked "v." case citations in course, statute, and doctrine pages
  link-doctrines    Add [[wikilinks]] to unlinked doctrine mentions in course, statute, and doctrine pages
  link-statutes     Add [[wikilinks]] to unlinked statute citations in course, statute, and doctrine pages
  link-shorthands   Add [[wikilinks]] to italic/alias shorthand case mentions
  update-index      Add missing pages (courses, cases, doctrines, statutes) to wiki/index.md
  create-stubs      Create stub pages for cases that are cited but have no wiki page yet
  validate          Check structural completeness: stubs, missing headings, unsourced-but-cited pages
  clean-reports     Delete old report files, keeping the 5 most recent of each type
  all               Run all commands in dependency order
"""

import argparse
import re
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT      = Path(__file__).parent.parent
WIKI      = ROOT / 'wiki'
COURSES   = WIKI / 'courses'
CASES     = WIKI / 'cases'
DOCTRINES = WIKI / 'doctrines'
STATUTES  = WIKI / 'statutes'
REPORTS   = Path(__file__).parent / 'reports'
RAW       = ROOT / 'raw'
EXTRACTED = RAW / 'extracted'

# ── Module-level compiled patterns ────────────────────────────────────────────

# Splitting with a capturing group returns wikilinks interleaved with segments:
# re.split(r'(\[\[...\]\])', text) → [seg, link, seg, link, ..., seg]
# Even indices are plain text; odd indices are wikilinks (preserved unchanged).
_WIKILINK_SPLIT = re.compile(r'(\[\[[^\]]*\]\])')

# Matches any [[wikilink]] without capturing (used for stripping/substitution)
_WIKILINK_RE = re.compile(r'\[\[[^\]]*\]\]')

# ── link-cases patterns (module-level so compiled once) ───────────────────────

_CASE_RE = re.compile(
    r'([A-Z][A-Za-z&\'\. ]{1,50})\bv\.\s+([A-Z][A-Za-z&\'\. ]{1,50})'
)
_NOISE_TRAIL = re.compile(
    r'\s+(rule|test|doctrine|factors|analysis|elements|approach|standard'
    r'|exception|principle|cases?|holding|rationale)s?$',
    re.IGNORECASE,
)
_NOISE_LEAD = re.compile(r'^(Compare|Overrules?|See also|Cf\.)\s+', re.IGNORECASE)

# Abbreviation normalization (longest key first so U.S. matches before U.S)
_ABBR = {
    'U.S.': 'United States', 'U.S': 'United States', 'US': 'United States',
    'L.A.': 'Los Angeles',   'LA':  'Los Angeles',
    'N.Y.': 'New York',      'NY':  'New York',
    "Dep't": 'Department', "Ass'n": 'Association', "Int'l": 'International',
}
_ABBR_RE = re.compile(
    r'\b(' + '|'.join(re.escape(k) for k in sorted(_ABBR, key=len, reverse=True)) + r')\b'
)

# ── link-statutes patterns (module-level so compiled once) ───────────────────

# Extracts acronym from a statute page title parenthetical: (APA), (FSIA), (RICO)
_STAT_ACR_RE = re.compile(r'\(([A-Z][A-Z0-9\-]{1,9})\)')

# Extracts ALL section numbers from a statute page title in one pass.
# Handles single sections (§ 553), comma-separated (§§ 1341, 1343),
# and ranges (§§ 1602–1611).  Group 1 = digit string(s) after the § sign.
_STAT_SEC_RE = re.compile(r'§+\s*([\d]+(?:\s*[,–\-]\s*[\d]+)*)')

# Scans course text for any bare § citation (for unmatched-section reporting).
# Group 1 = base section number.
_STAT_CITE_RE = re.compile(
    r'(?:\d{1,2}\s+U\.S\.C\.?\s+)?'    # optional "28 U.S.C. " prefix
    r'§{1,2}\s*'                         # § or §§
    r'(\d+)'                             # base section number (group 1)
    r'(?!\d)'                            # must not run into a longer number
    r'(?:\([a-zA-Z0-9]+\))*'            # optional subsections: (a), (2), (b)(3)
    r'(?:\s*[–\-]\s*\d+)?'             # optional range end: –1968
)

# Short act names that are ordinary English words also used for non-§-1441 doctrines.
# Prevents e.g. "Removal" (§ 1441) from linking presidential-removal-power text.
_EXCLUDED_SHORT_NAMES = {'Removal', 'Change', 'Final', 'Discovery'}

# Acronyms that appear in course files and may or may not have a statute page.
# Used by cmd_link_statutes to report unlinked references for gap-filling.
_KNOWN_ACRONYMS = re.compile(
    r'\b(APA|RICO|FSIA|ATS|MPC|MRPC|FRCP|FRE|UCC|DGCL|FMLA|FTCA|RFRA|AEDPA'
    r'|EEOC|NLRA|NLRB|ADEA|ERISA|FLSA|FCPA|SOX|CFPB|CFTC|DOJ|SEC|SCA|ECPA)\b'
)

# ── link-shorthands patterns (module-level so compiled once) ──────────────────

_ITALIC_RE = re.compile(r'\*([A-Z][A-Za-z &\'\.\-]{1,50}?)\*')
_PAREN_RE  = re.compile(r'\(([A-Z][A-Za-z &\'\.\-/]{1,50}?)\)')
_PAREN_SKIP = re.compile(
    r'^\d|§|see |citing |quoting |emphasis|hereinafter|internal|footnote'
    r'|omitted|alterations|citation|e\.g\.|i\.e\.|supra|infra|id\.',
    re.IGNORECASE,
)

_FRONTMATTER_RE = re.compile(r'^(---\n.*?\n---\n)', re.DOTALL)

# ── Shared helpers ─────────────────────────────────────────────────────────────

def parse_tags(content):
    """Extract tags from YAML frontmatter as a set of lowercase strings."""
    m = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return set()
    front = m.group(1)
    # Inline format: tags: [tag1, tag2]
    tm = re.search(r'tags:\s*\[([^\]]+)\]', front)
    if tm:
        return {t.strip().strip('"\'') for t in tm.group(1).split(',')}
    # Block format: tags:\n  - tag
    tags, in_tags = set(), False
    for line in front.split('\n'):
        if line.startswith('tags:'):       # startswith beats re.match for prefix check
            in_tags = True
            continue
        if in_tags:
            lm = re.match(r'\s*-\s*(.+)', line)
            if lm:
                tags.add(lm.group(1).strip().strip('"\''))
            elif line.strip() and not line[0].isspace():
                break
    return tags


# Tags that are broad enough to appear legitimately in many courses
CROSS_CUTTING = {
    'constitutional-law', 'federal-courts', 'evidence',
    'federal-question', 'jurisdiction',
}


def tags_compatible(case_tags, course_tags):
    """Return True if the case's subject is compatible with the course's subject."""
    if not case_tags or not course_tags:
        return False
    if case_tags & course_tags:
        return True
    if case_tags <= CROSS_CUTTING:
        return True
    return False


def _normalize(name):
    """Expand common abbreviations for fuzzy case-name matching."""
    return _ABBR_RE.sub(lambda m: _ABBR[m.group(0)], name).strip()


def _norm_case(stem):
    """Normalize a case page stem for duplicate detection."""
    return _normalize(stem).rstrip('.,').lower()


def all_pages():
    """Return set of all wiki page names (filename stem, no .md).

    Scans all four subdirectories plus the wiki root so that top-level pages
    (index, log, overview, and any future additions) are included without
    requiring a hardcoded list.
    """
    pages = set()
    if WIKI.exists():
        # Top-level pages (index.md, log.md, overview.md, …)
        for f in WIKI.iterdir():
            if f.suffix == '.md' and f.is_file():
                pages.add(f.stem)
    for d in [CASES, DOCTRINES, STATUTES, COURSES]:
        if d.exists():
            for f in d.iterdir():
                if f.suffix == '.md':
                    pages.add(f.stem)
    return pages


def course_files():
    """Yield (path, content) for each course .md file."""
    if not COURSES.exists():
        return
    for f in sorted(COURSES.iterdir()):
        if f.suffix == '.md':
            yield f, f.read_text()


def split_frontmatter(content):
    """Return (frontmatter, body) — frontmatter includes the closing --- line."""
    m = _FRONTMATTER_RE.match(content)
    if m:
        return m.group(1), content[m.end():]
    return '', content


@lru_cache(maxsize=512)
def _safe_link_pat(search):
    """Compile and cache the word-boundary pattern for `search`."""
    return re.compile(r'(?<![A-Za-z])' + re.escape(search) + r'(?![A-Za-z])')


def safe_link(content, search, page=None, display=None):
    """
    Replace plain `search` text with a [[page|display]] wikilink.
    Skips occurrences already inside [[ ]] and skips the YAML frontmatter.
    Idempotent and word-boundary aware.

    Uses a capturing-group split so one regex pass produces both the plain-text
    segments (even indices) and the existing wikilinks (odd indices, preserved).
    Returns (new_content, count_of_replacements_made).
    """
    if page is None:
        page = search
    if display is None:
        display = search
    wl  = f'[[{page}]]' if page == display else f'[[{page}|{display}]]'
    pat = _safe_link_pat(search)

    count = 0
    def repl(_):
        nonlocal count
        count += 1
        return wl

    fm, body = split_frontmatter(content)
    # Split with capturing group: [seg, link, seg, link, ..., seg]
    parts     = _WIKILINK_SPLIT.split(body)
    new_parts = [pat.sub(repl, p) if i % 2 == 0 else p for i, p in enumerate(parts)]
    return fm + ''.join(new_parts), count


def write_report(name, lines):
    """Write lines to tools/reports/<name>-<timestamp>.md and print the path."""
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = REPORTS / f'{name}-{ts}.md'
    path.write_text('\n'.join(lines) + '\n')
    print(f'Report → {path}')
    return path


# ── lint patterns (module-level so compiled once) ────────────────────────────

_USC_EXACT       = re.compile(r'(\d+)\s+U\.S\.C\.?\s*§+\s*(\d+[a-z]?)')
_US_V_RE         = re.compile(r'^U\.S\.\s+v\.')
_WORD_SEC_RE     = re.compile(r'\bSection\s+\d', re.IGNORECASE)
_CODE_ACRONYM    = re.compile(r'\b(?:MPC|MRPC|FRCP|FRE|UCC|DGCL|APA|NLRA|RICO|FSIA|ATS)\b')
_INTL_INSTRUMENT = re.compile(
    r'\b(?:Convention|Protocol|Agreement|Treaty|Charter|Directive)\b',
    re.IGNORECASE,
)

# ── validate / lint patterns (module-level so compiled once) ─────────────────
_CORE_HEADINGS_RE = re.compile(r'^## (Definition|Elements|Rule)\b', re.MULTILINE)
_SOURCES_VAL_RE   = re.compile(r'^sources:\s*(\d+)',                re.MULTILINE)
_SOURCES_ZERO_RE  = re.compile(r'^sources:\s*0\s*$',               re.MULTILINE)

# ── ingest patterns (module-level so compiled once) ──────────────────────────
_SEMESTER_RE  = re.compile(
    r'[_\-]?(FL|SP|Fa|Su|Fall|Spring|Summer)\s*(\d{2,4})$', re.IGNORECASE
)
_LOG_OP_RE    = re.compile(
    r'^## \[[\d\- :]+\] (ingest-start|ingest-complete)\b'
)
_LOG_SOURCE_RE = re.compile(r'^Source:\s*(.+)$')

# ── shared file iterators ─────────────────────────────────────────────────────

def all_wiki_files():
    """Yield (path, content) for every .md file under wiki/."""
    for d in [COURSES, CASES, DOCTRINES, STATUTES]:
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.suffix == '.md':
                    yield f, f.read_text()


def all_linkable_files():
    """Return list of (path, content) for courses + statutes + doctrines.

    Used by link-cases to determine which files to scan for case citations.
    cmd_lint derives the same set by filtering all_wiki_files() directly.
    """
    statute_files  = [(f, f.read_text()) for f in sorted(STATUTES.iterdir())  if f.suffix == '.md'] \
                     if STATUTES.exists() else []
    doctrine_files = [(f, f.read_text()) for f in sorted(DOCTRINES.iterdir()) if f.suffix == '.md'] \
                     if DOCTRINES.exists() else []
    return list(course_files()) + statute_files + doctrine_files


# ── ingest helpers ────────────────────────────────────────────────────────────

def _source_title(stem):
    """Convert a filename stem to a human-readable title.

    Examples:
      Contracts_I_FL15   → Contracts I (FL15)
      Antitrust-SP2017   → Antitrust (SP17)
    """
    m = _SEMESTER_RE.search(stem)
    if m:
        base   = stem[:m.start()]
        season = m.group(1).upper()
        year   = m.group(2)[-2:]   # last two digits
        base   = base.replace('_', ' ').replace('-', ' ').strip()
        return f'{base} ({season}{year})'
    return stem.replace('_', ' ').replace('-', ' ').strip()


def _resolve_source(arg):
    """Find a source file given a filename or path argument.

    Tries in order:
      1. Literal path (if exists)
      2. EXTRACTED / arg
      3. EXTRACTED / (arg + '.txt')
      4. RAW / 'notes' / arg
      5. Recursive RAW.rglob(arg)

    Returns Path if found, None otherwise.
    """
    p = Path(arg)
    if p.exists():
        return p
    candidate = EXTRACTED / arg
    if candidate.exists():
        return candidate
    candidate = EXTRACTED / (arg + '.txt')
    if candidate.exists():
        return candidate
    candidate = RAW / 'notes' / arg
    if candidate.exists():
        return candidate
    hits = list(RAW.rglob(arg))
    if hits:
        return hits[0]
    return None


def _ingested_sources():
    """Parse wiki/log.md and return (complete_stems, inprogress_stems).

    Scans log entries for ingest-start and ingest-complete headers.
    A source is 'complete' if it has an ingest-complete entry.
    A source is 'inprogress' if it has ingest-start but no ingest-complete.
    """
    log_path = WIKI / 'log.md'
    if not log_path.exists():
        return set(), set()

    complete    = set()
    inprogress  = set()
    current_op  = None   # 'ingest-start' | 'ingest-complete' | None

    for line in log_path.read_text().splitlines():
        m_op = _LOG_OP_RE.match(line)
        if m_op:
            current_op = m_op.group(1)
            continue
        # Any other ## heading resets current_op
        if line.startswith('## '):
            current_op = None
            continue
        if current_op is not None:
            m_src = _LOG_SOURCE_RE.match(line)
            if m_src:
                stem = Path(m_src.group(1).strip()).stem
                if current_op == 'ingest-complete':
                    complete.add(stem)
                    inprogress.discard(stem)
                elif current_op == 'ingest-start':
                    if stem not in complete:
                        inprogress.add(stem)
                current_op = None

    return complete, inprogress


def _unprocessed_sources():
    """Return sorted list of .txt files in EXTRACTED whose stems are not complete."""
    if not EXTRACTED.exists():
        return []
    complete, _ = _ingested_sources()
    return sorted(
        f for f in EXTRACTED.iterdir()
        if f.suffix == '.txt' and f.stem not in complete
    )


def _append_log(entry):
    """Append entry to wiki/log.md, creating the file with a header if needed."""
    log_path = WIKI / 'log.md'
    WIKI.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        existing = log_path.read_text()
        if existing and not existing.endswith('\n\n'):
            sep = '' if existing.endswith('\n') else '\n'
            log_path.write_text(existing + sep + '\n' + entry + '\n')
        else:
            log_path.write_text(existing + entry + '\n')
    else:
        log_path.write_text('# Wiki Log\n\n' + entry + '\n')


def _extract_source_cases(content):
    """Extract unique 'Plaintiff v. Defendant' strings from source text.

    Applies the same plaintiff/defendant cleaning as _scan_missing_cases.
    Returns a set of strings.
    """
    clean   = _WIKILINK_RE.sub('', content)
    results = set()
    for m in _CASE_RE.finditer(clean):
        plaintiff = ' '.join(m.group(1).split()).rstrip()
        defendant = ' '.join(m.group(2).split()).rstrip('. ,;:()\n*')
        if len(plaintiff) < 2 or len(defendant) < 2:
            continue
        if not plaintiff[0].isupper() or not defendant[0].isupper():
            continue
        full = f'{plaintiff} v. {defendant}'
        if _NOISE_TRAIL.search(full) or _NOISE_LEAD.match(full):
            continue
        results.add(full)
    return results


def _detect_doctrine_coverage(content, doctrine_pages):
    """Return sorted list of doctrine names that appear in the source text.

    Builds one alternation regex (longest names first) with word-boundary
    lookarounds. Returns sorted list of matched doctrine names.
    """
    if not doctrine_pages:
        return []
    # Sort longest first for greedy matching (already passed in sorted order
    # but enforce it here for safety)
    ordered = sorted(doctrine_pages, key=len, reverse=True)
    doc_re  = re.compile(
        r'(?<![A-Za-z])('
        + '|'.join(re.escape(d) for d in ordered)
        + r')(?![A-Za-z])'
    )
    matched = set(m.group(1) for m in doc_re.finditer(content))
    return sorted(matched)


def _detect_subject(stem):
    """Infer subject from filename stem by matching against course page names.

    1. Strip semester code using _SEMESTER_RE.
    2. Replace underscores/hyphens with spaces.
    3. Try substring match against existing course page names.
    4. Return longest match; fall back to cleaned name title-cased.
    """
    m    = _SEMESTER_RE.search(stem)
    base = stem[:m.start()] if m else stem
    base = base.replace('_', ' ').replace('-', ' ').strip()

    if COURSES.exists():
        course_names = [f.stem for f in COURSES.iterdir() if f.suffix == '.md']
        # Exact match first (case-insensitive) to avoid "Contracts I" matching
        # "Contracts II" via longest-substring.
        for c in course_names:
            if c.lower() == base.lower():
                return c
        matches = [
            c for c in course_names
            if base.lower() in c.lower() or c.lower() in base.lower()
        ]
        if matches:
            return max(matches, key=len)

    return base.title()


def _analyze_source(fpath, force):
    """Read and analyze one source file.

    Returns analysis dict or None if the source should be skipped.

    Dict keys: fpath, stem, title, source_rel, words, subject,
               case_mentions (set), covered_doctrines (list).
    """
    complete, inprogress = _ingested_sources()

    if fpath.stem in complete and not force:
        print(f'  skip (already complete): {fpath.name}')
        return None

    if fpath.stem in inprogress and not force:
        print(f'  note (resuming in-progress): {fpath.name}')

    content = fpath.read_text(errors='replace')
    words   = len(content.split())

    subject = _detect_subject(fpath.stem)

    case_mentions = _extract_source_cases(content)

    doctrine_pages = sorted(
        (f.stem for f in DOCTRINES.iterdir() if f.suffix == '.md'),
        key=len, reverse=True,
    ) if DOCTRINES.exists() else []

    covered_doctrines = _detect_doctrine_coverage(content, doctrine_pages)

    try:
        source_rel = str(fpath.relative_to(ROOT))
    except ValueError:
        source_rel = str(fpath)

    return {
        'fpath':             fpath,
        'stem':              fpath.stem,
        'title':             _source_title(fpath.stem),
        'source_rel':        source_rel,
        'words':             words,
        'subject':           subject,
        'case_mentions':     case_mentions,
        'covered_doctrines': covered_doctrines,
    }


def _write_brief(a, citation_counts, stub_stems, pages, fw_index, dry_run):
    """Generate and write the ingest brief for one source analysis.

    a               — analysis dict from _analyze_source
    citation_counts — {page_name: int} pre-computed across all wiki files
    stub_stems      — set of case page stems that are still stubs
    pages           — set of all wiki page names (from all_pages())
    fw_index        — first-word case index (from _build_case_index)
    dry_run         — if True, print path but do not write file

    Returns the report path.
    """
    slug = re.sub(r'[^a-z0-9]+', '-', a['stem'].lower()).strip('-')

    # Classify each case mention
    stubs   = []   # (citation_count, page)
    rich    = []   # page name (already-done)
    missing = []   # raw case string (no page yet)

    for case_str in sorted(a['case_mentions']):
        parts     = case_str.split(' v. ', 1)
        plaintiff = parts[0].strip()
        defendant = parts[1].strip() if len(parts) > 1 else ''
        page = _find_case_page(plaintiff, defendant, pages, fw_index)
        if page:
            if page in stub_stems or page.replace(' v. ', ' v ') in stub_stems:
                stubs.append((citation_counts.get(page, 0), page))
            else:
                rich.append(page)
        else:
            missing.append(case_str)

    stubs.sort(key=lambda x: x[0], reverse=True)   # most-cited stubs first

    # Build doctrine rows
    doctrine_rows = []
    for doctrine in a['covered_doctrines']:
        doc_path = DOCTRINES / f'{doctrine}.md'
        sources  = 0
        if doc_path.exists():
            sm = _SOURCES_VAL_RE.search(doc_path.read_text())
            if sm:
                sources = int(sm.group(1))
        action = 'fill in' if sources == 0 else 'enrich'
        doctrine_rows.append((doctrine, sources, action))

    ts = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines = [
        f'# Ingest Brief — {a["fpath"].name}',
        f'_Generated {ts}_',
        f'Source: `{a["source_rel"]}`',
        '',
    ]

    # ## Source
    lines += [
        '## Source',
        f'- **Words:** {a["words"]:,}',
        f'- **Detected subject:** {a["subject"]}',
        '',
    ]

    # ## Conversation opener
    lines += [
        '## Conversation opener',
        '',
        (f'> Please ingest `{a["source_rel"]}` into the wiki. '
         f'The detected subject is **{a["subject"]}**. '
         f'Focus on the pages listed in this brief. '
         f'Do not rewrite doctrine or case pages that already have sources ≥ 1 '
         f'unless you are adding genuinely new information.'),
        '',
        '---',
        '',
    ]

    # ## Doctrine pages to write or enrich
    if doctrine_rows:
        lines += [
            '## Doctrine pages to write or enrich',
            '',
            '| Page | sources | Action |',
            '|------|---------|--------|',
        ]
        for doctrine, sources, action in doctrine_rows:
            lines.append(f'| [[{doctrine}]] | {sources} | {action} |')
        lines.append('')

    # ## Case pages to fill in
    case_table_rows = [(count, page, 'stub') for count, page in stubs] + \
                      [(0, c, 'missing') for c in missing]
    if case_table_rows:
        lines += [
            '## Case pages to fill in',
            '',
            '| Case | Status | Cited in wiki |',
            '|------|--------|---------------|',
        ]
        for count, name, status in case_table_rows:
            lines.append(f'| [[{name}]] | {status} | {count}× |')
        lines.append('')

    # ## Cases already done
    if rich:
        lines += ['## Cases already done', '']
        for page in sorted(rich):
            lines.append(f'- [[{page}]]')
        lines.append('')

    # ## Summary
    lines += [
        '## Summary',
        '',
        f'- Doctrines detected: {len(doctrine_rows)}',
        f'- Case stubs to fill: {len(stubs)}',
        f'- Cases missing pages: {len(missing)}',
        f'- Cases already done: {len(rich)}',
        '',
    ]

    return write_report(f'ingest-brief-{slug}', lines)


def cmd_lint(dry_run, verbose):
    """Report broken wikilinks and unlinked case citations across all wiki pages."""
    pages  = all_pages()
    report = ['# Lint Report', f'_Generated {datetime.now():%Y-%m-%d %H:%M}_', '']
    total  = 0

    # Read every wiki file once; reused by checks 1 and 2.
    wiki_files = list(all_wiki_files())

    # ── 1. Broken wikilinks ───────────────────────────────────────────────────
    for fpath, content in wiki_files:
        links   = re.findall(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]', content)
        # Normalize trailing punctuation so [[Inc.]] resolves to file stem "Inc".
        # Skip targets starting with '[' — artifact of [[[wikilink]]] bracket notation.
        missing = sorted(set(
            l for l in links
            if not l.startswith('[') and l not in pages and l.rstrip('.,;') not in pages
        ))
        if missing:
            report.append(f'## {fpath.parent.name}/{fpath.name}')
            for m in missing:
                report.append(f'- `[[{m}]]`')
                total += 1
            report.append('')

    report.append(f'**Total broken links: {total}**')
    print(f'Broken links: {total}')

    # ── 2. Case citations with no wiki page ───────────────────────────────────
    # Filter wiki_files to the linkable set (courses + statutes + doctrines,
    # no case pages) — same scope as link-cases, without re-reading disk.
    fw_index      = _build_case_index(pages)
    linkable      = [(f, c) for f, c in wiki_files if f.parent != CASES]
    missing_cases = _scan_missing_cases(linkable, pages, fw_index)

    if missing_cases:
        total_missing = sum(len(v) for v in missing_cases.values())
        report += ['', '## Case citations missing wiki pages',
                   '_These "X v. Y" mentions appear in wiki files but have no page yet._', '']
        for fname in sorted(missing_cases):
            report.append(f'### {fname}')
            for c in missing_cases[fname]:
                report.append(f'- {c}')
            report.append('')
        report.append(f'**Cases missing pages: {total_missing}**')
        print(f'Cases missing pages: {total_missing}')

    # ── 3. Redundant pages ────────────────────────────────────────────────────
    # Case duplicates: two pages whose stems normalize to the same string.
    # _norm_case() is module-level; uses _normalize() + lowercase + strip punct.
    case_files = sorted(CASES.iterdir())    if CASES.exists()    else []
    stat_files = sorted(STATUTES.iterdir()) if STATUTES.exists() else []

    norm_to_cases = defaultdict(list)
    for f in case_files:
        if f.suffix == '.md':
            norm_to_cases[_norm_case(f.stem)].append(f.name)
    case_dups = {k: v for k, v in norm_to_cases.items() if len(v) > 1}

    # Statute duplicates: two pages that share the exact same (title, section).
    # Uses an alpha-suffix-aware pattern so § 77k ≠ § 77a (parent range start),
    # preventing false positives from parent-act + subsection page pairs.
    # (_USC_EXACT compiled once at module level.)
    sec_to_stats = defaultdict(list)
    for f in stat_files:
        if f.suffix == '.md':
            for m in _USC_EXACT.finditer(f.stem):
                sec_to_stats[(m.group(1), m.group(2))].append(f.name)
    stat_dups = {
        f'{t} U.S.C. § {s}': files
        for (t, s), files in sec_to_stats.items() if len(files) > 1
    }

    if case_dups or stat_dups:
        report += ['', '## Redundant pages',
                   '_Pages that appear to cover the same case or statute._', '']
        if case_dups:
            report.append('### Cases')
            for norm, files in sorted(case_dups.items()):
                report.append('- ' + ' · '.join(f'`{f}`' for f in files))
            report.append('')
        if stat_dups:
            report.append('### Statutes')
            for sec, files in sorted(stat_dups.items()):
                report.append(f'- **{sec}**: ' + ' · '.join(f'`{f}`' for f in files))
            report.append('')
        n_dups = sum(len(v) for v in case_dups.values()) + sum(len(v) for v in stat_dups.values())
        print(f'Redundant pages: {n_dups} files in {len(case_dups) + len(stat_dups)} clusters')

    # ── 4. Naming convention violations ──────────────────────────────────────
    # Flags deviations from wiki page-naming conventions:
    #   Cases    — "U.S. v." party abbreviation instead of "United States v."
    #              (Note: trailing "Co.." / "Corp.." double-periods are intentional —
    #              they reflect case names that end in an abbreviation.  True
    #              duplicates of that form are caught by check 3 above.)
    #   Statutes — "Section N" word form instead of the § symbol
    #            — title with no § and no recognized model-code acronym
    # (Patterns _US_V_RE, _WORD_SEC_RE, _CODE_ACRONYM, _INTL_INSTRUMENT are
    #  compiled once at module level above.)
    conv = []
    for f in case_files:
        if f.suffix != '.md':
            continue
        if _US_V_RE.match(f.stem):
            conv.append(
                f'cases/{f.name} — use "United States v." not "U.S. v."'
            )
    for f in stat_files:
        if f.suffix != '.md':
            continue
        if _WORD_SEC_RE.search(f.stem):
            conv.append(
                f'statutes/{f.name} — use "§ N" not "Section N" in title'
            )
        # Flag if no § in the title AND no recognized model-code acronym AND not
        # an international instrument.  Acceptable without a § or acronym:
        #   • "42 U.S.C. § 1983" (§ present)
        #   • "Model Penal Code (MPC)" (acronym present)
        #   • "Hague Service Convention" (Convention keyword present)
        if '§' not in f.stem and not _CODE_ACRONYM.search(f.stem) \
                and not _INTL_INSTRUMENT.search(f.stem):
            conv.append(
                f'statutes/{f.name} — missing § or code acronym in title'
            )

    if conv:
        report += ['', '## Naming convention violations', '']
        for v in sorted(conv):
            report.append(f'- {v}')
        report.append('')
        print(f'Naming violations: {len(conv)}')

    # ── 5. Tag quality ────────────────────────────────────────────────────────
    # Pages with no tags are invisible to tags_compatible(), so link-shorthands
    # and link-statutes will never link to or from them.  Flag them so tags can
    # be added during the next ingest or cleanup pass.
    # Exempt pages with sources: 0 — those are stubs that haven't been enriched
    # yet; it's expected and unavoidable that they lack tags until ingest fills
    # them in.  A page with sources ≥ 1 that has no tags is a real gap.
    # (_SOURCES_ZERO_RE compiled at module level.)
    tagless = [
        f'{fpath.parent.name}/{fpath.name}'
        for fpath, content in wiki_files
        if not parse_tags(content) and not _SOURCES_ZERO_RE.search(content)
    ]
    if tagless:
        report += ['', '## Pages with no tags',
                   '_Tags are required for subject-compatibility filtering (link-shorthands, link-statutes)._',
                   '']
        for f in sorted(tagless):
            report.append(f'- `{f}`')
        report.append(f'**Tagless pages: {len(tagless)}**')
        print(f'Tagless pages: {len(tagless)}')

    write_report('lint', report)


# ── link-cases ────────────────────────────────────────────────────────────────

def _build_case_index(pages):
    """Build first-word index over case pages for O(1) lookup.

    Returns fw_index: {first_word_of_plaintiff: [page_name, ...]}.
    """
    fw_index = {}
    for pg in pages:
        if ' v. ' not in pg:
            continue
        parts = pg.split(' v. ')[0].split()
        if parts:
            fw_index.setdefault(parts[0], []).append(pg)
    return fw_index


def _find_case_page(plaintiff, defendant, pages, fw_index):
    """Return the wiki page name matching plaintiff + defendant, or None."""
    full = f'{plaintiff} v. {defendant}'
    if full in pages:
        return full
    if full.rstrip('.') in pages:
        return full.rstrip('.')
    norm_p    = _normalize(plaintiff)
    norm_d    = _normalize(defendant)
    norm_full = f'{norm_p} v. {norm_d}'
    if norm_full in pages:
        return norm_full
    if norm_full.rstrip('.') in pages:
        return norm_full.rstrip('.')
    np_words = norm_p.split() or plaintiff.split()
    p1 = np_words[0] if np_words else ''
    d5 = (norm_d or defendant)[:5]
    for pg in fw_index.get(p1, []):
        if d5 in pg.split(' v. ', 1)[1]:
            return pg
    return None


def _scan_missing_cases(file_list, pages, fw_index):
    """Scan files for 'X v. Y' citations that have no wiki page.

    Returns dict {filename: [sorted list of missing case names]}.
    Used by both cmd_lint and cmd_link_cases so the check stays in sync.
    """
    missing_index = {}
    for fpath, content in file_list:
        clean   = _WIKILINK_RE.sub('', content)
        missing = []
        for m in _CASE_RE.finditer(clean):
            plaintiff = ' '.join(m.group(1).split()).rstrip()
            defendant = ' '.join(m.group(2).split()).rstrip('. ,;:()\n*')
            if len(plaintiff) < 2 or len(defendant) < 2:
                continue
            if not plaintiff[0].isupper() or not defendant[0].isupper():
                continue
            full = f'{plaintiff} v. {defendant}'
            if _NOISE_TRAIL.search(full) or _NOISE_LEAD.match(full):
                continue
            if not _find_case_page(plaintiff, defendant, pages, fw_index):
                missing.append(full)
        if missing:
            missing_index[fpath.name] = sorted(set(missing))
    return missing_index


def cmd_link_cases(dry_run, verbose):
    """Add wikilinks to unlinked 'X v. Y' case citations in course, statute, and doctrine pages.

    Also reports all 'v.' citations that have no matching wiki page so that
    missing pages can be identified and created in future sessions.
    """
    pages    = all_pages()
    fw_index = _build_case_index(pages)

    report        = ['# Link-Cases Report', f'_Generated {datetime.now():%Y-%m-%d %H:%M}_', '']
    total_links   = 0
    total_files   = 0
    missing_index = {}

    for fpath, content in all_linkable_files():
        clean         = _WIKILINK_RE.sub('', content)
        hits, missing = [], []

        for m in _CASE_RE.finditer(clean):
            plaintiff = ' '.join(m.group(1).split()).rstrip()
            defendant = ' '.join(m.group(2).split()).rstrip('. ,;:()\n*')
            if len(plaintiff) < 2 or len(defendant) < 2:
                continue
            if not plaintiff[0].isupper() or not defendant[0].isupper():
                continue
            full = f'{plaintiff} v. {defendant}'
            if _NOISE_TRAIL.search(full) or _NOISE_LEAD.match(full):
                continue
            page = _find_case_page(plaintiff, defendant, pages, fw_index)
            if page:
                hits.append((full, page))
            else:
                missing.append(full)

        new_content = content
        file_links  = 0

        if hits:
            report.append(f'## {fpath.name}')
            for display_name, page in sorted(set(hits)):
                new_content, added = safe_link(new_content, display_name, page, display_name)
                if added:
                    report.append(f'- `{display_name}` → `[[{page}]]` (+{added})')
                    file_links  += added
                    total_links += added
            report.append('')

        if file_links and not dry_run:
            fpath.write_text(new_content)
            total_files += 1

        if missing:
            missing_index[fpath.name] = sorted(set(missing))

    suffix  = ' *(dry run)*' if dry_run else ''
    summary = f'**Links added: {total_links} across {total_files} files{suffix}**'
    report.append(summary)
    print(summary)

    if missing_index:
        report += ['', '## Cases with no wiki page',
                   '_These citations appear in course files but have no matching page._', '']
        for fname in sorted(missing_index):
            report.append(f'### {fname}')
            for c in missing_index[fname]:
                report.append(f'- {c}')
            report.append('')
        total_missing = sum(len(v) for v in missing_index.values())
        msg = f'Cases missing pages: {total_missing}'
        report.append(f'**{msg}**')
        print(msg)

    write_report('link-cases', report)


# ── create-stubs ──────────────────────────────────────────────────────────────

def cmd_create_stubs(dry_run, verbose):
    """Create stub pages for cases that are cited but have no wiki page yet.

    Scans the same file set as link-cases, collects every 'X v. Y' citation
    with no matching page, and writes a minimal stub under wiki/cases/.
    Run this before link-cases so the stubs exist and can be linked in the
    same pass.
    """
    pages    = all_pages()
    fw_index = _build_case_index(pages)
    missing  = _scan_missing_cases(all_linkable_files(), pages, fw_index)

    # Deduplicate across files
    all_missing = sorted(set(c for cases in missing.values() for c in cases))

    report  = ['# Create-Stubs Report', f'_Generated {datetime.now():%Y-%m-%d %H:%M}_', '']
    created = 0
    skipped = 0
    today   = datetime.now().strftime('%Y-%m-%d')

    CASES.mkdir(parents=True, exist_ok=True)

    for case_name in all_missing:
        path = CASES / f'{case_name}.md'
        if path.exists():
            skipped += 1
            continue
        stub = (
            f'---\ntype: case\ntags: []\nsources: 0\nupdated: {today}\n---\n\n'
            f'# {case_name}\n\n'
            '## Citation\nStub — to be completed.\n\n'
            '## Facts\nStub — to be completed.\n\n'
            '## Issue\nStub — to be completed.\n\n'
            '## Holding\nStub — to be completed.\n\n'
            '## Rule\nStub — to be completed.\n\n'
            '## Significance\nStub — to be completed.\n\n'
            '## Courses\n- (no course page yet)\n'
        )
        report.append(f'- `{case_name}.md`')
        created += 1
        if not dry_run:
            path.write_text(stub)

    suffix  = ' *(dry run)*' if dry_run else ''
    summary = f'**Stubs created: {created} | already existed: {skipped}{suffix}**'
    report += ['', summary]
    print(summary)
    write_report('create-stubs', report)


# ── link-doctrines ────────────────────────────────────────────────────────────

def cmd_link_doctrines(dry_run, verbose):
    """Add wikilinks to unlinked doctrine mentions in course, statute, and doctrine pages.

    Builds a single alternation regex (longest name first so "Negligence Per Se"
    matches before "Negligence") and applies it in one pass per file instead of
    one pass per doctrine.
    """
    doctrine_pages = sorted(
        (f.stem for f in DOCTRINES.iterdir() if f.suffix == '.md'),
        key=len, reverse=True,
    )
    if not doctrine_pages:
        print('No doctrine pages found.')
        return

    # Single alternation regex — no need to exclude [ ] since we split first
    doc_re = re.compile(
        r'(?<![A-Za-z])('
        + '|'.join(re.escape(d) for d in doctrine_pages)
        + r')(?![A-Za-z])'
    )

    report      = ['# Link-Doctrines Report', f'_Generated {datetime.now():%Y-%m-%d %H:%M}_', '']
    total_links = 0
    total_files = 0

    for fpath, content in all_linkable_files():
        counts   = {}
        own_name = fpath.stem   # skip self-links on doctrine pages

        def replacer(m):
            d = m.group(1)
            if d == own_name:   # don't link a doctrine to itself
                return d
            counts[d] = counts.get(d, 0) + 1
            return f'[[{d}]]'

        # Apply only to body (skip frontmatter) and non-linked segments
        fm, body    = split_frontmatter(content)
        parts       = _WIKILINK_SPLIT.split(body)
        new_parts   = [doc_re.sub(replacer, p) if i % 2 == 0 else p
                       for i, p in enumerate(parts)]
        new_content = fm + ''.join(new_parts)

        if not counts:
            continue

        file_links   = sum(counts.values())
        total_links += file_links
        report.append(f'## {fpath.name}')
        for doctrine, count in sorted(counts.items()):
            report.append(f'- `[[{doctrine}]]` (+{count})')
        report.append('')

        if not dry_run:
            fpath.write_text(new_content)
            total_files += 1

    suffix  = ' *(dry run)*' if dry_run else ''
    summary = f'**Links added: {total_links} across {total_files} files{suffix}**'
    report.append(summary)
    print(summary)
    write_report('link-doctrines', report)


# ── link-statutes ─────────────────────────────────────────────────────────────

def _build_statute_index():
    """Return (name_aliases, sec_to_pages, page_tags) from wiki/statutes/ pages.

    name_aliases — {alias_str: page_name} for acronyms, short act names, and full
                   USC citations extracted from page titles.  Globally unambiguous;
                   no tags-compatibility check needed when linking.

    sec_to_pages — {section_number_str: [page_name, ...]} mapping every section
                   number found in any statute page title to all pages that claim it.
                   Ambiguity (same number on multiple pages) is resolved per-course
                   in cmd_link_statutes using tags-compatibility: a section is linked
                   only when exactly one candidate page is compatible with the course.

    page_tags    — {page_name: set_of_tags} for use in compatibility filtering.
    """
    name_aliases = {}
    sec_to_pages = {}   # sec_str → [pages]
    page_tags    = {}

    for f in STATUTES.iterdir():
        if f.suffix != '.md':
            continue
        page = f.stem
        page_tags[page] = parse_tags(f.read_text())

        # 1. Acronyms in (XXX) parentheticals: (APA), (FSIA), (MPC) …
        for m in _STAT_ACR_RE.finditer(page):
            acr = m.group(1)
            if len(acr) >= 2:
                name_aliases.setdefault(acr, page)

        # 2. Short act name = text before the first " (" in the title
        #    e.g. "Sherman Act" from "Sherman Act (15 U.S.C. §§ 1–2)"
        #    Also handles titles like "UCC Article 2" with no parenthetical by
        #    extracting the first all-caps word group as a separate alias.
        short = re.split(r'\s+\(', page)[0].strip()
        if short and short != page and len(short) >= 2 and short not in _EXCLUDED_SHORT_NAMES:
            name_aliases.setdefault(short, page)
        # For titles with no parenthetical (short == page), try to extract a
        # leading all-caps acronym, e.g. "UCC" from "UCC Article 2"
        leading_acr = re.match(r'^([A-Z]{2,10})\b', page)
        if leading_acr and short == page:
            name_aliases.setdefault(leading_acr.group(1), page)

        # 3. Full USC citation inside the title, normalised to strip trailing noise
        #    e.g. "15 U.S.C. §§ 1–2" from "Sherman Act (15 U.S.C. §§ 1–2)"
        usc_m = re.search(
            r'(\d{1,2}\s+U\.S\.C\.(?:\.|\s)\s*§{1,2}\s*[\d][\d\s\-–,a-z\(\)]*)',
            page, re.IGNORECASE,
        )
        if usc_m:
            usc = usc_m.group(1).strip().rstrip(',–- )')
            name_aliases.setdefault(usc, page)

        # 4. Collect section numbers for the unambiguous-section index.
        #    _STAT_SEC_RE captures the full digit string after §, including
        #    comma-separated and range-separated groups:
        #      "§ 553"          → nums = [553]
        #      "§§ 1341, 1343"  → nums = [1341, 1343]
        #      "§§ 1602–1611"   → nums = [1602, 1611]  then expanded to 1602…1611
        page_secs: set = set()
        for m in _STAT_SEC_RE.finditer(page):
            group = m.group(1)
            nums = [int(n) for n in re.findall(r'\d+', group)]
            for n in nums:
                page_secs.add(str(n))
            # Expand intermediate section numbers ONLY for dash-separated ranges
            # (§§ 1602–1611 → expand 1603…1610).  Comma-separated lists like
            # §§ 1341, 1343 or §§ 4, 7 are NOT expanded to avoid false collisions.
            if len(nums) == 2 and re.search(r'[–\-]', group):
                lo, hi = min(nums), max(nums)
                if 0 < hi - lo <= 30:
                    for sec_num in range(lo + 1, hi):   # endpoints already added
                        page_secs.add(str(sec_num))
        for sec in page_secs:
            sec_to_pages.setdefault(sec, []).append(page)

    # Return all mappings — ambiguity is resolved per-course using tags-compatibility
    # in cmd_link_statutes.  A section number that maps to multiple statute pages can
    # still be linked unambiguously if only one of those pages is tags-compatible with
    # the course being processed (e.g. "§ 7" → Clayton Act § 7 in Antitrust,
    # NLRA § 7 in Legislation — different tags, no collision).
    return name_aliases, sec_to_pages, page_tags


def cmd_link_statutes(dry_run, verbose):
    """Add [[wikilinks]] to unlinked statute citations in course, statute, and doctrine pages.

    Three categories are handled in one pass:
      1. Acronyms / short names (APA, RICO, Sherman Act …) — globally unambiguous;
         no subject-compatibility check needed.
      2. Full USC citations ("28 U.S.C. § 1350") that match a statute page title.
      3. Bare section cites ("§ 3142(e)", "§§ 1961–1968") — linked only when the
         section number maps unambiguously to one statute page AND the statute's tags
         are compatible with the file's tags (prevents § 553 in Contracts II
         from linking to the APA page).

    Also reports statute acronyms/citations that appear in wiki files but have
    no matching wiki page, so gaps can be filled.
    """
    if not STATUTES.exists():
        print('No statutes directory found.')
        return

    name_aliases, sec_to_pages, page_tags = _build_statute_index()

    report = [
        '# Link-Statutes Report',
        f'_Generated {datetime.now():%Y-%m-%d %H:%M}_',
        '',
        (f'Name aliases: {len(name_aliases)} '
         f'| Unique section numbers: {len(sec_to_pages)}'),
        '',
    ]
    if verbose:
        report.append('## Alias index')
        for alias, page in sorted(name_aliases.items()):
            report.append(f'- `{alias}` → `{page}`')
        report.append('')

    # ── Pre-build alias regex (longest alias first, compiled once) ──────────
    # One alternation regex replaces N separate safe_link passes (was O(N×M)).
    # Word-boundary lookarounds prevent partial matches (e.g. "APA" inside "TAPA").
    alias_order = sorted(name_aliases, key=len, reverse=True)
    alias_re    = re.compile(
        r'(?<![A-Za-z])(' + '|'.join(re.escape(a) for a in alias_order) + r')(?![A-Za-z])'
    )

    total_links = 0
    total_files = 0
    missing_index = {}   # fname → {acronyms, sections}

    for fpath, content in all_linkable_files():
        file_tags = parse_tags(content)
        file_links = 0
        file_log   = []

        # ── 1. Name aliases (acronyms + short act names + full USC cites) ──────
        # Single alternation regex pass (longest alias first) replaces the old
        # per-alias safe_link loop.  Operates only on non-linked body segments
        # so existing wikilinks are never rewritten.
        fm, body = split_frontmatter(content)
        alias_counts: dict[str, int] = {}

        def _alias_repl(m):
            alias = m.group(1)
            alias_counts[alias] = alias_counts.get(alias, 0) + 1
            page = name_aliases[alias]
            return f'[[{page}|{alias}]]' if page != alias else f'[[{page}]]'

        parts    = _WIKILINK_SPLIT.split(body)
        new_body = ''.join(
            alias_re.sub(_alias_repl, p) if i % 2 == 0 else p
            for i, p in enumerate(parts)
        )

        for alias, cnt in alias_counts.items():
            page = name_aliases[alias]
            file_links += cnt
            file_log.append(f'- `{alias}` → `[[{page}|{alias}]]` (+{cnt})')

        new_content = fm + new_body
        body        = new_body   # steps 2 and 3 operate on this post-step-1 body

        # ── 2. Section citations (tags-compatible) ───────────────────────────
        # Build per-file map: section → page, keeping only sections where
        # exactly one candidate page is tags-compatible with this file.
        # This allows the same section number to exist on multiple pages
        # (e.g. "§ 7" → Clayton Act § 7 in Antitrust, NLRA § 7 in Legislation)
        # and resolves ambiguity via tags rather than requiring global uniqueness.
        compat = {}
        for sec, pages in sec_to_pages.items():
            matching = [pg for pg in pages
                        if tags_compatible(page_tags.get(pg, set()), file_tags)]
            if len(matching) == 1:
                compat[sec] = matching[0]

        if compat:
            # Single alternation regex, longest section numbers first.
            # (?!\d) prevents matching a section number that is a prefix of a longer
            # number not in the index (e.g. § 1 should not match within § 1983).
            sec_alts = sorted(compat, key=len, reverse=True)
            sec_pat = re.compile(
                r'(?:\d{1,2}\s+U\.S\.C\.?\s+)?'   # optional title prefix
                r'§{1,2}\s*'
                r'(' + '|'.join(re.escape(s) for s in sec_alts) + r')'
                r'(?!\d)'                           # not a prefix of a longer number
                r'(?:\([a-zA-Z0-9]+\))*'           # optional subsections: (a)(2)(B)
                r'(?:\s*[–\-]\s*\d+)?'             # optional range end: –1968
            )

            sec_counts = {}   # page → total replacement count

            def _sec_repl(m):
                pg = compat[m.group(1)]
                sec_counts[pg] = sec_counts.get(pg, 0) + 1
                return f'[[{pg}|{m.group(0)}]]'

            parts = _WIKILINK_SPLIT.split(body)
            body  = ''.join(
                sec_pat.sub(_sec_repl, p) if i % 2 == 0 else p
                for i, p in enumerate(parts)
            )
            new_content = fm + body

            for pg, cnt in sorted(sec_counts.items()):
                file_links += cnt
                file_log.append(f'- section cites → `[[{pg}]]` (+{cnt})')

        # ── 3. Track acronyms and section cites with no wiki page ────────────
        # body is already the post-step-2 body (frontmatter excluded)
        clean = _WIKILINK_RE.sub('', body)

        # Acronyms
        missed_acr = {
            m.group(0) for m in _KNOWN_ACRONYMS.finditer(clean)
            if m.group(0) not in name_aliases
        }

        # Bare § cites whose section number has no statute page at all
        # (neither in sec_to_page nor in any ambiguous set).
        # Skip numbers that ARE in sec_to_page — those were linked or were
        # tags-incompatible with this course (not a "missing page" situation).
        all_secs_in_index = set(sec_to_pages.keys())
        missed_secs = {}
        for m in _STAT_CITE_RE.finditer(clean):
            sec = m.group(1)
            if sec not in all_secs_in_index:
                missed_secs[sec] = missed_secs.get(sec, 0) + 1

        if missed_acr or missed_secs:
            missing_index[fpath.name] = {
                'acronyms': sorted(missed_acr),
                'sections': missed_secs,
            }

        if file_log:
            total_links += file_links
            report.append(f'## {fpath.name}')
            report.extend(file_log)
            report.append('')
            if not dry_run:
                fpath.write_text(new_content)
                total_files += 1

    suffix  = ' *(dry run)*' if dry_run else ''
    summary = f'**Links added: {total_links} across {total_files} files{suffix}**'
    report.append(summary)
    print(summary)

    if missing_index:
        report += ['', '## Unlinked references with no statute page', '']
        for fname in sorted(missing_index):
            entry = missing_index[fname]
            report.append(f'### {fname}')
            for acr in entry.get('acronyms', []):
                report.append(f'- `{acr}` *(acronym)*')
            for sec, cnt in sorted(entry.get('sections', {}).items(),
                                   key=lambda x: -x[1]):
                report.append(f'- `§ {sec}` ×{cnt} *(no page)*')
            report.append('')

    write_report('link-statutes', report)


# ── link-shorthands ───────────────────────────────────────────────────────────

def cmd_link_shorthands(dry_run, verbose):
    """Add wikilinks to shorthand case mentions in italic (*Erie*) or parenthetical ((Staples)) form."""

    # Read all linkable files once — reused for alias extraction and main scan
    all_files = list(all_linkable_files())

    # Source 1: existing [[Full Name|Short]] aliases already in wiki files
    alias_map = {}
    for _, content in all_files:
        for m in re.finditer(r'\[\[([^\]|]+)\|([^\]]+)\]\]', content):
            page, alias = m.group(1).strip(), m.group(2).strip()
            if ' v. ' in page:
                alias_map.setdefault(alias, page)

    # Source 2: first-party names from case filenames; keep only unambiguous ones
    first_party_map = {}
    skip_words      = {'The', 'Inc', 'LLC', 'Ltd', 'Corp', 'Co', 'In'}
    for f in CASES.iterdir():
        if f.suffix != '.md':
            continue
        page = f.stem
        if ' v. ' not in page:
            continue
        first = page.split(' v. ')[0].strip()
        words = [w for w in first.split()
                 if len(w) > 2 and w[0].isupper() and w not in skip_words]
        if not words:
            continue
        first_party_map.setdefault(words[0], []).append(page)

    ambiguous = {k: v for k, v in first_party_map.items() if len(v) > 1}
    unambig   = {k: v[0] for k, v in first_party_map.items() if len(v) == 1}

    # Alias map takes priority (more explicit)
    shorthand_map = {**unambig, **alias_map}

    # Build case tags index — only for pages actually in the shorthand map
    needed_pages    = set(shorthand_map.values())
    case_tags_index = {}
    for f in CASES.iterdir():
        if f.suffix == '.md' and f.stem in needed_pages:
            case_tags_index[f.stem] = parse_tags(f.read_text())

    report = [
        '# Link-Shorthands Report',
        f'_Generated {datetime.now():%Y-%m-%d %H:%M}_',
        '',
        (f'Dictionary: {len(shorthand_map)} entries '
         f'({len(alias_map)} aliases, {len(unambig)} unambiguous first-party names)'),
        '',
    ]

    if verbose and ambiguous:
        report.append('## Ambiguous shorthands skipped')
        for key, pgs in sorted(ambiguous.items()):
            report.append(f'- **{key}**: ' + ', '.join(f'`{p}`' for p in pgs))
        report.append('')

    def collect_hits(plain_text, course_tags):
        """Return (hits, skipped) scanning only plain (non-wikilink) text."""
        hits, skipped = [], []

        def check(candidate, label):
            if candidate not in shorthand_map:
                return
            page      = shorthand_map[candidate]
            case_tags = case_tags_index.get(page, set())
            if tags_compatible(case_tags, course_tags):
                hits.append((candidate, page, label))
            else:
                skipped.append((candidate, page, case_tags, label))

        for m in _ITALIC_RE.finditer(plain_text):
            check(m.group(1).strip(), 'italic')

        for m in _PAREN_RE.finditer(plain_text):
            candidate = m.group(1).strip()
            if not _PAREN_SKIP.search(candidate):
                check(candidate, 'paren')

        return hits, skipped

    def apply_hits(segments, hits):
        """Apply replacements to even-indexed (plain-text) segments only.

        Returns (new_segments, count, log_lines).  Skips odd-indexed segments
        (existing wikilinks) so already-linked text is never double-linked.
        """
        added, log = 0, []
        for display, page, label in sorted(set((d, p, l) for d, p, l in hits)):
            if label == 'italic':
                old, new = f'*{display}*', f'*[[{page}|{display}]]*'
            else:
                old, new = f'({display})', f'([[{page}|{display}]])'
            count = sum(seg.count(old) for i, seg in enumerate(segments) if i % 2 == 0)
            if count:
                segments = [
                    seg.replace(old, new) if i % 2 == 0 else seg
                    for i, seg in enumerate(segments)
                ]
                added += count
                log.append(f'- `{old}` → `[[{page}|{display}]]` (+{count})')
        return segments, added, log

    total_links = 0
    total_files = 0

    for fpath, content in all_files:
        file_tags = parse_tags(content)
        fm, body  = split_frontmatter(content)
        # Split body into alternating plain/wikilink segments; scan plain text only
        segments    = _WIKILINK_SPLIT.split(body)
        plain_text  = ''.join(s for i, s in enumerate(segments) if i % 2 == 0)

        hits, skipped = collect_hits(plain_text, file_tags)

        if not hits and (not verbose or not skipped):
            continue

        report.append(f'## {fpath.name}')
        segments, file_links, log_lines = apply_hits(segments, hits)
        new_content = fm + ''.join(segments)
        report.extend(log_lines)
        total_links += file_links

        if verbose and skipped:
            report.append('  _Skipped (subject mismatch):_')
            for display, page, ctags, label in sorted(set(
                (d, p, frozenset(t), l) for d, p, t, l in skipped
            )):
                fmt = f'`*{display}*`' if label == 'italic' else f'`({display})`'
                report.append(
                    f'  - {fmt} → `{page}` '
                    f'[tags: {", ".join(sorted(ctags)) or "none"}]'
                )

        report.append('')

        if file_links and not dry_run and new_content != content:
            fpath.write_text(new_content)
            total_files += 1

    suffix  = ' *(dry run)*' if dry_run else ''
    summary = f'**Links added: {total_links} across {total_files} files{suffix}**'
    report.append(summary)
    print(summary)
    write_report('link-shorthands', report)


# ── update-index ──────────────────────────────────────────────────────────────

def cmd_update_index(dry_run, verbose):
    """Add missing pages to the appropriate sections of wiki/index.md."""
    index_path = WIKI / 'index.md'
    if not index_path.exists():
        print('wiki/index.md not found — create it first (see CLAUDE.md).')
        return
    index = index_path.read_text()

    # Build set of already-indexed pages once
    indexed = set(re.findall(r'\[\[([^\]|]+)\]\]', index))

    def extract_summary(content, section_patterns):
        """Return first non-empty line under any matching ## heading."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.match(section_patterns, line):
                for j in range(i + 1, min(i + 5, len(lines))):
                    txt = lines[j].strip().lstrip('- *#')
                    if txt:
                        return txt[:75]
        return ''

    def new_rows_for(directory, section_patterns):
        """Return index rows for pages in `directory` not yet in the index."""
        rows = []
        if not directory.exists():
            return rows
        for f in sorted(directory.iterdir()):
            if f.suffix != '.md' or f.stem in indexed:
                continue
            content = f.read_text()
            date_m  = re.search(r'updated:\s*([\d-]+)', content)
            date    = date_m.group(1) if date_m else datetime.now().strftime('%Y-%m-%d')
            summary = extract_summary(content, section_patterns)
            rows.append(f'| [[{f.stem}]] | {summary} | {date} |')
        return rows

    course_rows   = new_rows_for(COURSES,   r'## (Overview|Topics|Key Doctrines|Course Description)')
    case_rows     = new_rows_for(CASES,     r'## (Significance|Rule|Holding)')
    doctrine_rows = new_rows_for(DOCTRINES, r'## (Definition|Elements|Rule)')
    statute_rows  = new_rows_for(STATUTES,  r'## (Overview|Key (Features|Provisions))')

    all_new = course_rows + case_rows + doctrine_rows + statute_rows
    report  = [
        '# Update-Index Report',
        f'_Generated {datetime.now():%Y-%m-%d %H:%M}_',
        '',
        (f'Courses: +{len(course_rows)} | Cases: +{len(case_rows)} '
         f'| Doctrines: +{len(doctrine_rows)} | Statutes: +{len(statute_rows)}'),
        '',
    ]
    if course_rows:
        report += ['### Courses'] + course_rows + ['']
    if case_rows:
        report += ['### Cases'] + case_rows + ['']
    if doctrine_rows:
        report += ['### Doctrines'] + doctrine_rows + ['']
    if statute_rows:
        report += ['### Statutes'] + statute_rows + ['']

    if all_new and not dry_run:
        def insert_rows(text, section_header, rows):
            """Append rows to the end of `section_header`'s table block."""
            if not rows:
                return text
            # Find the next ## heading after section_header to know where to insert
            pos = text.find(f'\n{section_header}\n')
            if pos == -1:
                return text + '\n' + '\n'.join(rows) + '\n'
            next_sec = text.find('\n## ', pos + 1)
            insert_at = next_sec if next_sec != -1 else len(text)
            return text[:insert_at] + '\n' + '\n'.join(rows) + text[insert_at:]

        index = insert_rows(index, '## Courses',   course_rows)
        index = insert_rows(index, '## Cases',     case_rows)
        index = insert_rows(index, '## Doctrines', doctrine_rows)
        index = insert_rows(index, '## Statutes',  statute_rows)
        index = re.sub(
            r'(updated:\s*)\d{4}-\d{2}-\d{2}',
            f'\\g<1>{datetime.now():%Y-%m-%d}',
            index, count=1,
        )
        index_path.write_text(index)

    suffix = ' *(dry run)*' if dry_run else ''
    print(f'Index entries added: {len(all_new)}{suffix}')
    write_report('update-index', report)


# ── clean-reports ─────────────────────────────────────────────────────────────

_REPORT_FILENAME_RE = re.compile(r'^(.+)-(\d{8}-\d{6})\.md$')
_REPORTS_KEEP = 5   # number of most-recent reports to retain per command type


def cmd_clean_reports(dry_run, verbose):
    """Delete old report files, keeping the 5 most recent of each type.

    Report filenames have the form <command>-YYYYMMDD-HHMMSS.md, so sorting
    alphabetically within each type gives chronological order.
    """
    if not REPORTS.exists():
        print('No reports directory — nothing to clean.')
        return

    by_type = defaultdict(list)
    for f in REPORTS.iterdir():
        m = _REPORT_FILENAME_RE.match(f.name)
        if m:
            by_type[m.group(1)].append(f)

    report  = ['# Clean-Reports Report', f'_Generated {datetime.now():%Y-%m-%d %H:%M}_', '']
    deleted = 0

    for cmd_type, files in sorted(by_type.items()):
        files.sort(key=lambda f: f.name, reverse=True)   # newest first
        to_delete = files[_REPORTS_KEEP:]
        if not to_delete:
            continue
        report.append(f'### {cmd_type} ({len(to_delete)} deleted, {_REPORTS_KEEP} kept)')
        for f in to_delete:
            report.append(f'- `{f.name}`')
            deleted += 1
            if not dry_run:
                f.unlink()
        report.append('')

    suffix  = ' *(dry run)*' if dry_run else ''
    summary = f'**Reports deleted: {deleted}{suffix}**'
    report.append(summary)
    print(summary)
    write_report('clean-reports', report)


# ── validate ──────────────────────────────────────────────────────────────────

def cmd_validate(dry_run, verbose):
    """Check wiki pages for structural completeness.

    Three checks:
      1. Stub case pages — pages still containing 'Stub — to be completed.',
         sorted by citation count so the most-referenced gaps surface first.
      2. Doctrine pages missing a Definition / Elements / Rule heading.
      3. Pages with sources: 0 that are cited 3+ times (should be enriched).

    Reads every wiki file exactly once; all three checks reuse that list.
    (_CORE_HEADINGS_RE, _SOURCES_VAL_RE, _H1_RE compiled at module level.)
    """
    CITE_THRESHOLD = 3

    # Single read pass — all three checks operate on this list.
    wiki_files = list(all_wiki_files())

    # ── Precompute citation counts (used by checks 1 and 3) ──────────────────
    citation_counts: dict[str, int] = defaultdict(int)
    for _, content in wiki_files:
        for m in re.finditer(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]', content):
            citation_counts[m.group(1).strip()] += 1

    report = ['# Validate Report', f'_Generated {datetime.now():%Y-%m-%d %H:%M}_', '']
    issues = 0

    # ── 1. Stub case pages ────────────────────────────────────────────────────
    stub_cases = [
        (citation_counts.get(fpath.stem, 0), fpath.stem)
        for fpath, content in wiki_files
        if fpath.parent == CASES and 'Stub — to be completed.' in content
    ]
    stub_cases.sort(reverse=True)   # most-cited stubs first

    if stub_cases:
        report += ['## Stub case pages (most-cited first)',
                   '_These pages have unfilled stub sections._', '']
        for count, name in stub_cases:
            report.append(f'- `{name}` — cited {count}× in the wiki')
        report.append(f'**Stub cases: {len(stub_cases)}**')
        report.append('')
        issues += len(stub_cases)
        print(f'Stub cases: {len(stub_cases)}')

    # ── 2. Doctrine pages missing core heading ────────────────────────────────
    incomplete_doctrines = [
        fpath.stem
        for fpath, content in wiki_files
        if fpath.parent == DOCTRINES and not _CORE_HEADINGS_RE.search(content)
    ]
    if incomplete_doctrines:
        report += ['## Doctrine pages missing Definition / Elements / Rule heading', '']
        for name in sorted(incomplete_doctrines):
            report.append(f'- `{name}`')
        report.append(f'**Incomplete doctrines: {len(incomplete_doctrines)}**')
        report.append('')
        issues += len(incomplete_doctrines)
        print(f'Incomplete doctrines: {len(incomplete_doctrines)}')

    # ── 3. Frequently-cited pages still at sources: 0 ────────────────────────
    # Use fpath.stem (not H1) for citation_counts lookup — wikilinks target the
    # filename stem, so H1 mismatches would silently zero-out the count.
    # Exclude pages already reported in check 1 (stubs) to avoid double-reporting.
    stub_stems = {name for _, name in stub_cases}
    unsourced  = []
    for fpath, content in wiki_files:
        if fpath.stem in stub_stems:
            continue
        sm = _SOURCES_VAL_RE.search(content)
        if sm and int(sm.group(1)) == 0:
            count = citation_counts.get(fpath.stem, 0)
            if count >= CITE_THRESHOLD:
                unsourced.append((count, fpath.stem))
    unsourced.sort(reverse=True)

    if unsourced:
        report += [f'## Frequently-cited pages with sources: 0 (cited ≥ {CITE_THRESHOLD}×)',
                   '_These pages are referenced often but have never been enriched from a source._',
                   '']
        for count, name in unsourced:
            report.append(f'- `{name}` — cited {count}×')
        report.append(f'**Unsourced but cited: {len(unsourced)}**')
        report.append('')
        issues += len(unsourced)
        print(f'Unsourced but cited: {len(unsourced)}')

    summary = f'**Total issues: {issues}**'
    report.append(summary)
    print(summary)
    write_report('validate', report)


# ── ingest ───────────────────────────────────────────────────────────────────

def cmd_ingest(source_arg, dry_run, verbose, brief_only, force, new):
    """Analyze source file(s), run maintenance pass, write ingest brief(s).

    Workflow:
      1. Locate source(s) — via --new (all unprocessed) or a named file.
      2. Analyze each source: detect subject, cases, and doctrine coverage.
      3. Write ingest-start log entries to wiki/log.md.
      4. Run maintenance pass (cmd_all) unless --brief-only or --dry-run.
      5. Write an ingest brief report for each source.
    """
    # ── Step 1 — Locate sources ───────────────────────────────────────────────
    fpaths = []

    if new and not source_arg:
        unprocessed = _unprocessed_sources()
        if not unprocessed:
            complete, inprogress = _ingested_sources()
            print(
                f'No new sources found. '
                f'({len(complete)} complete, {len(inprogress)} in-progress)'
            )
            return
        print(f'Unprocessed sources ({len(unprocessed)}):')
        for f in unprocessed:
            print(f'  {f.name}')
        fpaths = unprocessed

    elif source_arg:
        fpath = _resolve_source(source_arg)
        if fpath is None:
            print(f'Source not found: {source_arg!r}')
            available = sorted(EXTRACTED.iterdir())[:5] if EXTRACTED.exists() else []
            if available:
                print('Available files in raw/extracted/:')
                for f in available:
                    print(f'  {f.name}')
            return
        fpaths = [fpath]

    else:
        print('Usage: wiki.py ingest <source> [--dry-run] [--verbose] [--brief-only] [--force]')
        print('       wiki.py ingest --new')
        return

    # ── Step 2 — Analyze all sources ──────────────────────────────────────────
    analyses = []
    for fpath in fpaths:
        a = _analyze_source(fpath, force)
        if a is not None:
            analyses.append(a)

    if not analyses:
        print('Nothing to process.')
        return

    # ── Step 3 — Write ingest-start log entries ───────────────────────────────
    # Skip sources already in-progress (have ingest-start but no ingest-complete)
    # to avoid duplicate log entries when resuming an interrupted ingest.
    if not dry_run:
        _, inprogress_stems = _ingested_sources()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M')
        for a in analyses:
            if a['stem'] in inprogress_stems:
                continue   # already has an ingest-start entry — don't duplicate
            entry = (
                f'## [{ts}] ingest-start | {a["title"]}\n'
                f'Source: {a["source_rel"]}'
            )
            _append_log(entry)

    # ── Step 4 — Maintenance pass ─────────────────────────────────────────────
    if not brief_only and not dry_run:
        print('\n── maintenance pass ──')
        cmd_all(dry_run, verbose)

    # ── Step 5 — Write briefs ─────────────────────────────────────────────────
    # Precompute shared state once, after the maintenance pass so it reflects
    # the current state of the wiki.
    wiki_files_list = list(all_wiki_files())
    citation_counts = defaultdict(int)
    for _, content in wiki_files_list:
        for m in re.finditer(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]', content):
            citation_counts[m.group(1).strip()] += 1
    stub_stems = {
        fpath.stem for fpath, content in wiki_files_list
        if fpath.parent == CASES and 'Stub — to be completed.' in content
    }
    pages    = all_pages()
    fw_index = _build_case_index(pages)

    brief_paths = []
    for a in analyses:
        bp = _write_brief(a, citation_counts, stub_stems, pages, fw_index, dry_run)
        brief_paths.append(bp)

    print(f'\n── ingest complete ── ({len(brief_paths)} brief(s))')
    for bp in brief_paths:
        print(f'  {bp}')
    print('\nNext step: Open the brief(s) in Obsidian and start a Claude conversation.')


# ── all ───────────────────────────────────────────────────────────────────────

_ALL_SEQUENCE = [
    ('create-stubs',    cmd_create_stubs),   # create stubs first so link-cases can link to them
    ('link-cases',      cmd_link_cases),
    ('link-doctrines',  cmd_link_doctrines),
    ('link-statutes',   cmd_link_statutes),
    ('link-shorthands', cmd_link_shorthands),
    ('update-index',    cmd_update_index),
    ('validate',        cmd_validate),       # structural completeness check
    ('lint',            cmd_lint),           # wikilink health check — runs last
    # clean-reports is intentionally excluded: it deletes files and should be
    # run manually when you want to prune old reports, not on every maintenance pass.
    #   python tools/wiki.py clean-reports [--dry-run]
]

def cmd_all(dry_run, verbose):
    """Run every maintenance command in the correct dependency order."""
    for name, fn in _ALL_SEQUENCE:
        print(f'\n── {name} ──')
        fn(dry_run, verbose)


# ── CLI ───────────────────────────────────────────────────────────────────────

COMMANDS = {
    'ingest':          cmd_ingest,
    'lint':            cmd_lint,
    'link-cases':      cmd_link_cases,
    'link-doctrines':  cmd_link_doctrines,
    'link-statutes':   cmd_link_statutes,
    'link-shorthands': cmd_link_shorthands,
    'update-index':    cmd_update_index,
    'create-stubs':    cmd_create_stubs,
    'validate':        cmd_validate,
    'clean-reports':   cmd_clean_reports,
    'all':             cmd_all,
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='wiki.py — llm-wiki maintenance toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Commands:\n' + '\n'.join(f'  {k}' for k in COMMANDS),
    )
    parser.add_argument('command',   choices=COMMANDS)
    parser.add_argument('source',        nargs='?', default=None,
                        help='Source file path or name (ingest command only)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report only — do not write any files')
    parser.add_argument('--verbose', action='store_true',
                        help='Include skipped/ambiguous items in report')
    parser.add_argument('--new',         action='store_true',
                        help='ingest: process all unprocessed sources in raw/extracted/')
    parser.add_argument('--brief-only',  action='store_true',
                        help='ingest: generate brief without running maintenance pass')
    parser.add_argument('--force',       action='store_true',
                        help='ingest: re-process even if already logged as complete')
    args = parser.parse_args()
    if args.command == 'ingest':
        cmd_ingest(args.source, args.dry_run, args.verbose,
                   args.brief_only, args.force, args.new)
    else:
        COMMANDS[args.command](args.dry_run, args.verbose)
