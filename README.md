# Law School LLM Wiki — Example

A generated, browsable example of the [law-school-llm-wiki](https://github.com/legalrealist/law-school-llm-wiki) pattern: an AI-maintained law-school knowledge base built by [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) from course outlines, case briefs, and notes, then published as a [Quartz](https://quartz.jzhao.xyz/) site.

**[Browse the live wiki →](https://legalrealist.github.io/law-school-llm-wiki-example/)**

![The generated wiki: an Explorer sidebar (cases, courses, doctrines, statutes), an index page with Overview / Courses / Doctrines tables linking to per-topic pages like Constitutional Law, Torts, the Anti-Commandeering Doctrine, and Carolene Products Footnote 4, plus a graph view and table of contents](assets/screenshot.png)

Every doctrine, case, and course gets its own cross-linked page; the wiki is rebuilt and re-linked each time a new source is ingested, so knowledge compounds instead of being re-retrieved per question.

## How it was made

This site is the *output*. To build your own from your own materials, use the pattern repo:

- **[law-school-llm-wiki](https://github.com/legalrealist/law-school-llm-wiki)** — drop your outlines/briefs/notes into `raw/`, and Claude Code reads, extracts, and maintains the structured wiki.

Companion to the [LegalRealist AI Landscape](https://legalrealist.ai) series.
