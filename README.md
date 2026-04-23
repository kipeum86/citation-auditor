# citation-auditor

🌐 **Language**: **English** | [한국어](docs/ko/README.md)

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-orange.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Tests](https://img.shields.io/badge/tests-29%2F29_passing-brightgreen.svg)](tests/)

> **⚠️ AI-generated audits only. Always have outputs reviewed by a qualified professional.** This plugin flags suspicious citations and factual claims but does not replace human legal or domain expertise. A `✅` badge means *"no contradiction found"* — not *"confirmed correct beyond doubt."* Treat `⚠️` and `❓` as mandatory manual-review triggers.

**citation-auditor** is a pluggable fact-check and citation audit layer for Claude Code. It takes markdown output from any AI agent, extracts factual claims, dispatches domain-specific verifier subagents, and returns the same markdown with inline verdict badges (✅ / ⚠️ / ❓) plus an appended Audit Report.

Designed for agents that generate content requiring citation accuracy — **legal opinions, medical summaries, financial analyses, academic briefs, journalistic drafts**. Bundled verifiers cover Korean law (via Korean-law MCP) and general web sources; the verifier interface is designed for third-party extension.

Part of the **AI Trust Infrastructure** series — the post-receive counterpart to `document-redactor`, which handles redaction *before* sending to AI.

---

## 📌 Platform Compatibility

> This is a **Claude Code plugin**. It does **NOT** work with:
> - Claude Desktop app
> - claude.ai web interface
> - Anthropic API (direct SDK usage)
> - Other AI coding assistants (Cursor, Zed, Windsurf, etc.)

The plugin relies on Claude Code-specific features: the skill format with frontmatter, slash commands, the Task tool for subagent dispatch, the Bash tool for utility invocation, and session-level MCP server integration. None of these are portable to other surfaces.

The Python utility layer (`python -m citation_auditor chunk|render|aggregate|korean_law …`) can be invoked as a CLI in any environment, but without the Claude Code-side orchestration the end-to-end verification flow does not run.

---

## 📖 Table of Contents

- [The Problem](#the-problem)
- [What It Does](#what-it-does)
- [What It Does NOT Do](#what-it-does-not-do)
- [How It Works](#how-it-works)
- [Bundled Verifiers](#bundled-verifiers)
- [Quick Start](#quick-start)
- [Live Example](#live-example)
- [Verification Boundary](#verification-boundary)
- [Privacy & Data](#privacy--data)
- [Extending with Custom Verifiers](#extending-with-custom-verifiers)
- [Development](#development)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Roadmap](#roadmap)
- [License](#license)

---

## The Problem

AI agents that write substantive documents routinely produce plausible-sounding but fabricated citations — across every domain:

- **Legal.** An opinion cites `42 U.S.C. § 1983` or `GDPR Article 17` for content that is not actually in the cited provision. A case citation (`Smith v. Jones, 547 U.S. 123 (2006)`) uses a real-looking Supreme Court reporter format but is entirely fabricated. A compliance memo references `GDPR Article 100` when the regulation has only 99 articles.
- **Medical.** A literature review cites "Lancet 2019;394:1234-45" for findings from a paper that was never published. A treatment protocol attributes dosing guidance to WHO Guidelines that do not contain that recommendation.
- **Financial.** A research brief claims "2023 semiconductor market grew 15%" when the actual SEMI industry figure is 3.4%. A due diligence memo cites "SEC Rule 10b5-1(c)(2)(iv)" when the rule stops at subsection (iii).
- **Academic / Historical.** A paper attributes a quote to "Einstein, 1953" that has no verifiable source. A history brief states "the Treaty of Westphalia was signed in 1653" (actual: 1648).
- **Journalistic.** An analysis piece says "according to a 2023 MIT study" when no such study exists, or cites a non-existent Pew Research poll.

Today a careful reviewer spends 10–30 minutes per document spot-checking each citation against authoritative sources. **citation-auditor compresses that review to ~5 minutes** by pre-flagging suspicious passages with visible `⚠️` / `❓` badges so the reviewer focuses only on what needs human judgment.

---

## What It Does

- **Extracts** verifiable factual claims and citations from markdown AI output
- **Routes** each claim to a domain-appropriate verifier skill
- **Dispatches** verifier subagents in parallel via Claude Code's Task tool
- **Aggregates** verdicts using authority-weighted consensus
- **Re-emits** the original markdown with inline verdict badges + an appended `## Audit Report` section
- **Preserves** all existing downstream pipelines (`md-to-docx.py`, etc.) without modification

## What It Does NOT Do

- **Legal advice, risk assessment, or strategic recommendations** — audit output is evidence-based fact-check only
- **Evaluation of speculation, forecasts, opinions, or rumors** — by design, sentences like *"industry sources expect regulation to loosen"* are excluded from the audit surface
- **Deep precedent body comparison** — for case citations we confirm existence + detect clear topic mismatches via search-result titles, but full-text judgment analysis is deferred to future versions
- **Legal reasoning evaluation** — whether a valid citation correctly supports the argument is not in scope
- **Automatic rewriting** — verdicts are annotations; rewriting suspicious passages is left to the human or to the upstream writing agent

---

## How It Works

**Three layers wrapped in a single Claude Code plugin:**

```
┌──────────────────────────────────────────────────────────────┐
│  Plugin  .claude-plugin/plugin.json + marketplace.json       │
│          declares commands/ and skills/ to Claude Code       │
└──────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴──────────────────────┐
        ▼                                            ▼
┌───────────────────────┐              ┌──────────────────────────┐
│  Skills   (primary)   │              │  Python  (deterministic) │
│                       │  bash call   │                          │
│  citation-auditor ────┼─────────────►│  chunk / aggregate /     │
│  verifiers/*          │   stdout     │  render / korean_law     │
└───────────────────────┘              └──────────────────────────┘
        │
        │ Task tool dispatch
        ▼
┌─────────────────────────────────────┐
│  Verifier subagents (parallel)      │
│  korean-law  → Korean-law MCP       │
│  general-web → WebSearch + WebFetch │
└─────────────────────────────────────┘
```

- **Skills drive orchestration.** The `citation-auditor` skill directs Claude through chunking → claim extraction → verifier routing → Task-based parallel verification → aggregation → rendering.
- **Python does only deterministic work.** Markdown AST chunking, reverse-offset badge insertion, verdict weighting, pydantic schema validation, Korean legal citation parsing. No LLM calls, no external API calls.
- **Verifiers are skill files.** Each verifier is a separate `skills/verifiers/<name>/SKILL.md` with frontmatter declaring `patterns` and `authority` plus a body describing the verification protocol. Claude loads the skill via Task tool subagent dispatch.

**CC-native design principle:** no separate Anthropic API key, no Tavily key, no LLM provider configuration. The Claude instance already running in your Claude Code session does all the reasoning. Privacy settings (e.g., `ANTHROPIC_BASE_URL` routing to a local endpoint) are inherited automatically.

---

## Bundled Verifiers

| Verifier | Authority | Pattern Matches | Mechanism |
|---|:---:|---|---|
| **`korean-law`** | 1.0 | 제N조, major Korean statute names, case numbers (`YYYY다/가/도…NNNNN`) | Korean-law MCP → statute text comparison (조/항/호 granularity) + precedent existence check + title-based topic mismatch detection |
| **`us-law`** | 0.9 | `<title> U.S.C. § <section>`, `<title> C.F.R. § <part>.<section>`, SCOTUS reporter citations (`<vol> U.S. <page>`), case names (`A v. B`) | Cornell LII (U.S.C./C.F.R.) + CourtListener v4 free REST (SCOTUS opinions) → canonical-page WebFetch → WebSearch fallback when WebFetch is empty/denied → claim text comparison |
| **`uk-law`** | 0.9 | UK neutral citations (UKSC, UKHL, UKPC, EWCA Civ/Crim, EWHC, UKUT), case names (`X v Y`), UK statute names (`<Name> Act <year>`) | BAILII (case law) + legislation.gov.uk (statutes) → canonical-page WebFetch → WebSearch fallback when WebFetch is empty/denied → claim text comparison |
| **`eu-law`** | 0.9 | CELEX numbers, `Regulation (EU) YYYY/N`, `Directive YYYY/N/EU`, named acts (GDPR, DSA, DMA, AI Act, eIDAS, MiCA, NIS 2, DSM, Data Act) | EUR-Lex via CELEX → ELI alias retry on empty body → WebSearch fallback → act/article-level claim comparison |
| **`scholarly`** | 0.9 | DOI (`10.XXXX/...`), arXiv IDs, PMID, structured journal citations | CrossRef + arXiv + PubMed E-utilities free APIs → citation existence and metadata (title/authors/year/journal) alignment check |
| **`wikipedia`** | 0.7 | Historical/biographical/founding-year language patterns | Wikipedia REST summary API (EN + KO) → entity page lookup → specific-fact cross-check, full-article WebFetch when summary is insufficient |
| **`general-web`** | 0.5 | `.*` (fallback for everything else) | WebSearch → select top 3 authoritative URLs → WebFetch each → LLM-based claim adjudication |

**Routing order:** `suggested_verifier` declared by the claim extractor → regex pattern match across loaded verifier skills → `general-web` fallback. When multiple verifiers match a single claim, all run in parallel via Task tool subagent dispatch.

**Verdict aggregation:** when multiple verifiers produce verdicts for the same claim, the higher-authority verdict wins. Equal-authority conflicts resolve to `❓` (conflict signal, not false confidence).

**Free, no-API-key design:** every bundled verifier uses either a Claude Code MCP (korean-law) or free public APIs without authentication (Cornell LII, CourtListener, BAILII, legislation.gov.uk, EUR-Lex, CrossRef, arXiv, PubMed, Wikipedia, general WebSearch/WebFetch). No setup beyond installing the plugin.

**WebSearch fallback (us-law / uk-law / eu-law):** these three verifiers fall back to domain-scoped `WebSearch` (e.g., `site:law.cornell.edu`, `site:bailii.org`, `site:eur-lex.europa.eu`) when the canonical WebFetch is permission-denied, blocked by anti-bot interstitials (BAILII serves an Anubis page), or returns a JS-rendered shell with empty body (EUR-Lex). The fallback preserves verdict accuracy in real-world environments where WebFetch is restricted.

---

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and working
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) on `PATH`
- (For `korean-law` verifier) Korean-law MCP server connected to your Claude Code session
- (For `us-law` / `uk-law` / `eu-law` / `general-web` verifiers) WebFetch + WebSearch available in your session

### Install

Inside a Claude Code session:

```
/plugin marketplace add kipeum86/citation-auditor
/plugin install citation-auditor@citation-auditor
```

Choose **User scope** when prompted. User scope installs to `~/.claude/` so the plugin becomes available across every Claude Code session without writing anything into your project repos.

### Reload

```
/reload-plugins
```

### Audit a markdown file

```
/citation-auditor:audit path/to/opinion.md
```

Output is the same file with `**[✅ verifier-name]**` / `**[⚠️ verifier-name]**` / `**[❓ verifier-name]**` badges after each audited sentence, followed by a `## Audit Report` section with rationale and evidence for every claim.

### Update

```
/plugin update citation-auditor@citation-auditor
```

---

## Live Example

The following is an illustrative synthetic example showing the pipeline on an English-language briefing draft. With the bundled `general-web` verifier, every claim below is routed through WebSearch + WebFetch against authoritative sources.

**Input** — an AI-drafted briefing with a mix of real, partially-true, and fabricated claims:

```markdown
The Supreme Court held in Miranda v. Arizona, 384 U.S. 436 (1966),
that custodial suspects must be informed of their rights before
interrogation.

GDPR Article 17 establishes the right to erasure, commonly known as
the "right to be forgotten."

A 2023 MIT study found that 73% of software engineers now use AI
coding assistants daily.

The Treaty of Westphalia was signed in 1653, ending the Thirty
Years' War.

Industry analysts expect the AI regulation landscape to loosen
substantially by late 2026.
```

**Annotated output after `/citation-auditor:audit`:**

```markdown
The Supreme Court held in Miranda v. Arizona, 384 U.S. 436 (1966),
that custodial suspects must be informed of their rights before
interrogation. **[✅ general-web]**

GDPR Article 17 establishes the right to erasure, commonly known as
the "right to be forgotten." **[✅ general-web]**

A 2023 MIT study found that 73% of software engineers now use AI
coding assistants daily. **[❓ general-web]**

The Treaty of Westphalia was signed in 1653, ending the Thirty
Years' War. **[⚠️ general-web]**

Industry analysts expect the AI regulation landscape to loosen
substantially by late 2026.

## Audit Report

### Claim 3
- Verdict: unknown
- Verifier: general-web
- Rationale: No MIT publication matching "73% of engineers use AI
  coding assistants daily" was located. A widely cited 2024 GitHub
  survey reports ~92%, but attribution to MIT and the exact 73%
  figure could not be corroborated.
- Evidence: https://github.blog/2024-...

### Claim 4
- Verdict: contradicted
- Verifier: general-web
- Rationale: The Peace of Westphalia was signed in 1648, not 1653.
  It did end the Thirty Years' War.
- Evidence: https://www.britannica.com/event/Peace-of-Westphalia
```

The speculative sentence ("Industry analysts expect...") carries no badge — it is excluded from the audit surface by design. See [Verification Boundary](#verification-boundary).

### End-to-End Validation

v1.0 was validated against a **10-claim legal memo** (mixed real and fabricated citations, Korean legal domain): **10/10 claims correctly classified**, surfacing 5 distinct hallucinations — a non-existent statute article, a second non-existent statute article, a non-existent case number, a real case number with a mismatched topic, and a false growth-rate claim (with the correct figure surfaced in the rationale). The full test artifact is preserved in `fixtures/` and reproducible by dropping it into the `/citation-auditor:audit` slash command with the `korean-law` verifier loaded.

v1.2 added the three new bundled legal verifiers (`us-law`, `uk-law`, `eu-law`) and was validated against a **6-claim global-legal briefing** (`fixtures/v1.2-global-legal.md`) mixing US, UK, and EU jurisdictions with three real and three fabricated citations: **6/6 correctly classified**. The validation surfaced four real-world environment behaviors that the v1.2 WebSearch fallback handles correctly — Cornell LII WebFetch denial, BAILII Anubis anti-bot interstitial, EUR-Lex JS-rendered shell with empty body, and structurally impossible neutral citations (`[2024] UKSC 9876`, `CELEX 39999L8888`). Reproducible by dropping the fixture into `/citation-auditor:audit` with the three new verifiers loaded.

---

## Verification Boundary

citation-auditor audits **verifiable factual claims and citations**. The following are intentionally excluded from the audit surface:

| Category | Example | Handled? |
|---|---|:---:|
| Statute citation | "GDPR Article 17 requires data erasure upon request." | ✅ Audited |
| Case citation | "Miranda v. Arizona, 384 U.S. 436 (1966), held that..." | ✅ Audited |
| Regulatory reference | "HIPAA § 164.502(a)(1) permits disclosure for treatment." | ✅ Audited |
| Quantitative fact | "The 2023 global semiconductor market reached $527B." | ✅ Audited |
| Historical fact | "The Treaty of Westphalia was signed in 1648." | ✅ Audited |
| Scientific citation | "Lancet 2019;394:1234-45 reported a 23% reduction in..." | ✅ Audited |
| Forecast / prediction | "Regulators are expected to loosen these rules by 2026." | ❌ Not audited |
| Industry rumor | "Industry sources say the merger will close next quarter." | ❌ Not audited |
| Opinion / value judgment | "This approach is reasonable and well-considered." | ❌ Not audited |
| Legal / logical reasoning | "Therefore, the clause is void." (conclusion drawn from cited law) | ❌ Not audited |

Unaudited sentences carry no badge; they are the reviewer's responsibility.

---

## Privacy & Data

- **No separate API keys.** The plugin inherits your Claude Code session's Anthropic credentials and any configured `ANTHROPIC_BASE_URL` (including routes to local Ollama endpoints).
- **No telemetry.** The plugin does not collect usage data or phone home.
- **Web queries only via bundled verifiers.** The `general-web` verifier uses WebSearch and WebFetch (provided by your Claude Code session). If your session restricts or blocks those, the verifier returns `❓` and does not exfiltrate content elsewhere.
- **Korean legal queries** go to the Korean-law MCP server configured in your Claude Code session. Per-query content depends on that MCP's implementation.
- **`local_only` mode.** Both bundled verifiers support an opt-in `local_only` flag that skips all outbound network calls and returns `❓ "local-only mode"` for any claim that would otherwise require web or MCP lookup.

When processing sensitive documents (privileged legal matters, PHI, PII), configure your Claude Code session's data-retention and base-URL settings according to your organization's policy *before* running the audit. The plugin does not add or override those settings.

Anthropic official references:
- [Claude Code data usage](https://docs.anthropic.com/en/docs/claude-code/data-usage)
- [Commercial data retention](https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)

---

## Extending with Custom Verifiers

A verifier is a single skill file at `skills/verifiers/<your-name>/SKILL.md` with the following frontmatter:

```yaml
---
name: your-verifier-name
description: One-line summary of what you verify.
patterns:
  - "regex-pattern-1"
  - "regex-pattern-2"
authority: 0.7          # between 0.0 and 1.0
disable-model-invocation: true
---
```

The body describes the verification protocol: how to accept a claim as JSON, which tools to call (MCP, WebFetch, or any other tool available to a Claude Code subagent), and how to emit a verdict JSON conforming to `{label, rationale, supporting_urls, authority}`.

Full specification including the JSON input/output contract is in [skills/README.md](skills/README.md). A complete working reference is the bundled `korean-law` verifier at [skills/verifiers/korean-law/SKILL.md](skills/verifiers/korean-law/SKILL.md).

**Ideas for domain verifiers** the community could ship:
- `sec-filings` (EDGAR API for 10-K/10-Q/8-K filings, Rule citations)
- `clinicaltrials` (ClinicalTrials.gov API v2 for NCT numbers)
- `github-refs` (GitHub + npm + PyPI package/repo existence, NVD CVE)
- `financial-stats` (FRED, BoK API)
- `cjeu-cases` (Court of Justice of the European Union case law beyond Regulations/Directives)
- `patents` (USPTO PatentsView, EPO)
- `pubmed-clinical` (PubMed full-article cross-check beyond `scholarly` metadata)

---

## Development

```bash
git clone https://github.com/kipeum86/citation-auditor
cd citation-auditor
uv sync --group dev
uv run pytest
```

29 tests cover the Python utility layer (chunking, rendering, aggregation, Korean legal citation parsing). Skills are tested end-to-end inside a real Claude Code session since they involve LLM orchestration and tool dispatch.

Smoke test the CLI utilities directly:

```bash
echo -e "Alpha.\n\n민법 제103조에 따른 법률행위는 무효이다." > /tmp/test.md
uv run python -m citation_auditor chunk /tmp/test.md --max-tokens 3000
uv run python -m citation_auditor korean_law parse "민법 제103조"
```

---

## Project Structure

```
citation-auditor/
├── .claude-plugin/
│   ├── plugin.json               # Claude Code plugin manifest
│   └── marketplace.json          # Single-plugin marketplace descriptor
├── commands/
│   └── audit.md                  # /audit slash command (→ citation-auditor skill)
├── skills/
│   ├── README.md                 # Third-party verifier authoring guide
│   ├── citation-auditor/
│   │   └── SKILL.md              # Primary orchestration skill
│   └── verifiers/
│       ├── general-web/SKILL.md  # WebSearch + WebFetch fallback verifier
│       ├── korean-law/SKILL.md   # Korean-law MCP verifier (statute + precedent)
│       ├── us-law/SKILL.md       # Cornell LII + CourtListener verifier (USC, CFR, SCOTUS)
│       ├── uk-law/SKILL.md       # BAILII + legislation.gov.uk verifier (neutral citations, statutes)
│       ├── eu-law/SKILL.md       # EUR-Lex verifier (CELEX, Regulations, Directives, named acts)
│       ├── scholarly/SKILL.md    # CrossRef + arXiv + PubMed citation verifier
│       └── wikipedia/SKILL.md    # Wikipedia REST API verifier (EN + KO)
├── citation_auditor/             # Python utility package (deterministic only)
│   ├── __main__.py               # CLI entry: chunk|aggregate|render|korean_law
│   ├── chunking.py               # Markdown AST chunking with paragraph overlap
│   ├── render.py                 # Marko-based badge insertion + Audit Report
│   ├── aggregation.py            # Authority-weighted verdict consensus
│   ├── models.py                 # Pydantic schemas (Claim, Verdict, etc.)
│   ├── settings.py               # AuditSettings (no API keys)
│   └── korean_law.py             # Citation parsing, hang/ho extraction, case-number normalization
├── docs/
│   ├── day1-mcp-resolution.md    # Korean-law MCP capability spike notes
│   └── ko/
│       └── README.md             # Korean mirror of this document
├── tests/                         # 29 pytest cases
├── fixtures/                      # Synthetic test opinions
├── CHANGELOG.md
├── LICENSE                        # Apache License 2.0
├── pyproject.toml                 # pydantic + marko runtime; pytest dev
└── README.md                      # This file
```

---

## Requirements

- Claude Code (current version recommended)
- Python 3.11+
- `uv` for environment management
- Optional: Korean-law MCP server (for `korean-law` verifier)
- Optional: WebFetch + WebSearch enabled in your Claude Code session (for `general-web` verifier)

Runtime Python dependencies are intentionally minimal: `pydantic` and `marko`. No HTTP clients, no external SDKs, no LLM providers.

---

## Roadmap

**v1.0 (shipped — 2026-04-22)**
- Skill-primary architecture with Python deterministic utilities
- Bundled `korean-law` and `general-web` verifiers
- Third-party verifier extension contract
- Markdown-in / markdown-out; zero downstream pipeline modification
- 10/10 accuracy on live E2E test of a mixed real/fabricated citation opinion

**v1.1 (shipped — 2026-04-22)**
- `scholarly` verifier: DOI, arXiv, PMID citation verification via CrossRef/arXiv/PubMed free APIs
- `wikipedia` verifier: general-knowledge fact verification via Wikipedia REST API (EN + KO)
- Bilingual README overhaul with cross-domain examples (legal / medical / financial / academic / journalistic)
- All bundled verifiers now free & no-auth: no API keys required for any verifier

**v1.x (planned)**
- `SubagentStop` hook for automatic post-generation audit
- Feedback loop mode: return `⚠️` / `❓` claims to the upstream writing agent for revision
- MCP tool form: expose `verify_claim` as an MCP tool callable from any CC-compatible client
- Privacy end-to-end tests against local Ollama endpoints
- OpenAI / additional provider support through CC's existing provider abstraction
- Frontmatter `metadata:` migration for schema compliance

Release notes: [CHANGELOG.md](CHANGELOG.md)

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
