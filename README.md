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
| **`korean-law`** | 1.0 | 제N조, 주요 법령명, 판례번호 | Korean-law MCP → statute text comparison (조/항/호 granularity) + precedent existence check + title-based topic mismatch detection |
| **`general-web`** | 0.5 | `.*` (fallback for all claims) | WebSearch → select top 3 authoritative URLs → WebFetch each → LLM-based claim adjudication |

**Verdict aggregation:** when multiple verifiers match the same claim, the higher-authority verdict wins. Equal-authority conflicts resolve to `❓` (conflict signal, not false confidence).

---

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and working
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) on `PATH`
- (For `korean-law` verifier) Korean-law MCP server connected to your Claude Code session
- (For `general-web` verifier) WebFetch + WebSearch available in your session

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

The snippet below is from the **actual end-to-end test run** used to validate v1.0 — a Korean game-industry legal memo mixing real and fabricated citations. We show it in Korean because that's the authentic run; the same pipeline applies to any language and domain provided a suitable verifier skill is loaded (see [Extending with Custom Verifiers](#extending-with-custom-verifiers)).

Non-Korean-speaking readers: every Korean line below is a factual or citation-bearing claim. The verifier proved `⚠️` / `❓` / `✅` judgments using Korean statute text, precedent search, and Korean web sources — the same way a `us-law` verifier would use Westlaw/CourtListener, or a `pubmed` verifier would use PubMed.

**Input** — an AI-drafted legal memo with a mix of real and fabricated citations:

```markdown
계약의 유효성 판단에 있어 민법 제103조는 선량한 풍속 기타 사회질서에
위반한 사항을 내용으로 하는 법률행위는 무효로 한다고 규정한다.

게임산업진흥에 관한 법률 제300조 제5항은 확률형 아이템의 개별 확률을
소수점 다섯 자리까지 공시할 것을 의무화한다고 규정한다.

대법원 2023다302036 판결은 확률형 아이템 소비자 보호 의무 위반 시
사업자의 손해배상 책임을 인정한 선례이다.

2023년 한국 게임 시장 규모는 약 22조 원으로, 전년 대비 15% 성장하였다.
```

**Annotated output after `/citation-auditor:audit`:**

```markdown
계약의 유효성 판단에 있어 민법 제103조는 선량한 풍속 기타 사회질서에
위반한 사항을 내용으로 하는 법률행위는 무효로 한다고 규정한다.
**[✅ korean-law]**

게임산업진흥에 관한 법률 제300조 제5항은 확률형 아이템의 개별 확률을
소수점 다섯 자리까지 공시할 것을 의무화한다고 규정한다.
**[⚠️ korean-law]**

대법원 2023다302036 판결은 확률형 아이템 소비자 보호 의무 위반 시
사업자의 손해배상 책임을 인정한 선례이다.
**[⚠️ korean-law]**

2023년 한국 게임 시장 규모는 약 22조 원으로, 전년 대비 15% 성장하였다.
**[⚠️ general-web]**

## Audit Report

### Claim 2
- Verdict: contradicted
- Verifier: korean-law
- Rationale: 게임산업진흥에 관한 법률에 제300조는 존재하지 않습니다.

### Claim 3
- Verdict: contradicted
- Verifier: korean-law
- Rationale: 사건번호는 확인되지만, 판례의 실제 쟁점이 주장과 다릅니다.
  (판례 요지: "이 사건 확약서, 이 사건 특약사항은 모두 민법 제103조에서
  정한 반사회적 법률행위에 해당하여 무효에 해당함")
- Evidence: law.go.kr 판례 검색 결과 ID 245007

### Claim 4
- Verdict: contradicted
- Verifier: general-web
- Rationale: 2024 대한민국 게임백서에 따르면 2023년 국내 게임산업 매출은
  약 22조 9,642억 원으로 시장 규모 수치는 근사하나, 전년 대비 성장률은
  15%가 아닌 3.4%입니다.
- Evidence: https://zdnet.co.kr/view/?no=20250317111753
```

In live E2E testing on a 10-claim test opinion mixing real and fabricated citations, citation-auditor correctly classified all 10 claims including 5 hallucinations (missing statute articles, a missing case number, a precedent with mismatched topic, and a false growth rate with the correct figure surfaced in the rationale).

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
- `us-law` (Cornell LII, CourtListener)
- `pubmed` (PubMed E-utilities MCP)
- `eu-law` (EUR-Lex)
- `case-law-uk` (BAILII)
- `sec-filings` (EDGAR MCP)
- `financial-stats` (FRED, BoK API)

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
│       ├── general-web/SKILL.md  # WebSearch + WebFetch verifier
│       └── korean-law/SKILL.md   # Korean-law MCP verifier
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
