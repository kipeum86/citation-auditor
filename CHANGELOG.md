# Changelog

All notable changes to citation-auditor are documented here. This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] — 2026-04-27

### Added
- **DOCX input support** for `/citation-auditor:audit <file.docx>`. DOCX files are converted locally into audit-source markdown plus a source map; the original DOCX is not modified.
- **`python -m citation_auditor prepare <file.md|file.docx>`** — deterministic audit run path planning. For DOCX inputs it chooses safe temp paths plus `.audit.md` / `.audit.json` sidecar paths and refuses to overwrite existing sidecars unless `--overwrite` is supplied.
- **`python -m citation_auditor extract-docx <input.docx> --out-md <path> --out-map <path>`** — deterministic OOXML extraction using the Python standard library (`zipfile` + `xml.etree.ElementTree`). Extracts body paragraphs and table-cell text, records source block offsets, and rejects unsafe/oversized zip structures.
- **`python -m citation_auditor report <source-map.json> <aggregated.json> --out <file.audit.md>`** — renders sidecar audit reports for DOCX inputs with summary counts, finding table, source locations (`문단 N`, `표 N / 행 N / 열 N`), rationale, and evidence.
- **`python -m citation_auditor report ... --out-json <file.audit.json>`** — writes machine-readable report payloads with stable `summary`, `scope`, and `findings` fields for downstream automation and agent repair loops.
- **Source map schemas** (`SourceBlock`, `SourceMap`) for mapping aggregated claim offsets back to extracted DOCX source blocks.
- **Scope Notice** in DOCX sidecar reports, including extraction omissions such as footnotes, endnotes, comments, deleted tracked changes, images/OCR-only text, and unreconstructed Word numbering.
- **Optional `audit_reason` on claims** (`factual`, `citation`, `quantitative`, `temporal`) so the extractor can mark why uncited factual assertions entered the audit surface.
- **`fixtures/v1.4-docx-legal.docx`** and **`fixtures/v1.4-docx-legal.expected.md`** for a real Claude Code slash-command DOCX E2E run. The fixture covers Korean statutes, table-cell claims, EU law, a quantitative hallucination, and a forecast sentence that should be skipped.
- **`scripts/vendor-into.sh --confirm-docx-upgrade`** guard for applying v1.4+ over an existing v1.3 vendored copy. Dry runs now disclose that DOCX behavior will be enabled.
- **Explicit local-only slash-command flags**: `/citation-auditor:audit --local-only <file>`, `--no-web`, and `--offline`.

### Changed
- Primary `citation-auditor` skill now accepts `.md`, `.markdown`, and `.docx`. Markdown mode preserves the existing annotated-markdown output path; DOCX mode writes a sidecar `.audit.md` report and returns only the report path plus a concise summary.
- Primary `citation-auditor` skill now uses `prepare` output for audit input, temp aggregate files, source maps, and sidecar report paths instead of inventing placeholders in prompt text.
- Claim extraction guidance now covers verifiable factual claims even when no citation is attached, including dates, numeric claims, named legal authority or institutional action, and existence/non-existence claims.
- Bundled verifier routing fields moved from top-level frontmatter `patterns` / `authority` to `metadata.patterns` / `metadata.authority`; the primary skill still accepts the legacy fields as fallback for third-party verifiers.
- `/citation-auditor:audit` slash command description and argument hint now mention DOCX and local-only flags.
- README and Korean README updated for DOCX usage, v1.4.0 version badge, 52-test count, verifier metadata schema, local-only flags, vendor upgrade guard, and new CLI commands.
- Package/plugin versions bumped to `1.4.0` to avoid Claude Code plugin cache drift.

### Validation
- Component validation: Python utility suite expanded from 29 to **52 tests** covering audit path preparation, DOCX extraction, DOCX fixture extraction, table/paragraph source maps, extraction omission notices, deleted-text handling, source-map/chunk offset alignment, sidecar report rendering, report JSON payloads, verifier metadata schema, local-only command contract, vendor upgrade guards, new CLI commands, and all prior chunking/rendering/aggregation/Korean-law behavior.
- Component validation command: `uv run pytest` passes: **52 passed**.
- Real slash-command E2E: fixture and expected outcomes are prepared, but the live Claude Code `/citation-auditor:audit fixtures/v1.4-docx-legal.docx` run is tracked separately and should not be counted as passed until executed in a real CC session.

### Notes
- DOCX appendix export, Word comments, full footnote/endnote extraction, and tracked-change reconstruction remain future work. v1.4.0 intentionally ships the safer sidecar-report path first.
- Existing vendored legal-agent copies should not be bulk-updated just for DOCX support. Update one canary project only when that project actually needs DOCX auditing.

## [1.3.0] — 2026-04-24

### Added
- **`scripts/vendor-into.sh`** — rsync-based vendor script for copying citation-auditor into another CC-based project as local skills. Target receives `.claude/commands/audit.md`, `.claude/skills/citation-auditor/`, `.claude/skills/verifiers/*`, and the `citation_auditor/` Python package. Idempotent (re-run to update). Produces a `VENDOR.md` stamp in the target recording version, source commit, source tag, and timestamp.
  - Flags: `--dry-run` (preview), `--no-python` (skip Python package).
  - Pyproject dependency list and WebFetch allowlist are **printed as manual post-copy steps** rather than auto-merged, since target projects use varied TOML styles (uv, poetry, hatch, setuptools) that auto-merge can break.
- **README section — "Vendoring into another project"** (both English and Korean mirror) documenting when to pick plugin vs vendor and the full vendoring workflow.

### Fixed
- **Orchestration skill `skills/citation-auditor/SKILL.md` step 11**: added the exact aggregate input JSON schema with a concrete example. Previously the skill described the *contents* of aggregate input but did not specify the top-level wrapper key is `verdicts`, forcing Claude to reverse-engineer the schema from `citation_auditor/models.py` during real `/audit` runs. Surfaced during v1.2.0 E2E validation on `fixtures/v1.2-global-legal.md`.

### Validation
- **v1.2.0 real `/audit` E2E** (executed before tagging v1.3.0): user ran `/citation-auditor:audit fixtures/v1.2-global-legal.md` in a live CC terminal, end-to-end through plugin install → orchestration skill → claim extraction → parallel verifier subagents → aggregate → render. All 6 claims correctly classified (3 verified, 3 contradicted). WebSearch fallback fired on 4 of 6 claims (Cornell denied, BAILII Anubis, EUR-Lex JS shell) — confirming the v1.2 fallback design is a real-world primary path, not a defensive nicety. This was the first time the full production pipeline (as opposed to component + simulation testing) was exercised end to end.
- Vendor script dry-run + real copy verified into a temp target: 18 files copied (1 slash command, 1 orchestration skill, 7 verifier skills, 1 skills README, 7 Python files, 1 VENDOR.md stamp). Version parsing fixed to use `[[:space:]]` for BSD sed compatibility on macOS.

### Notes
- Plugin install path (`/plugin marketplace add kipeum86/citation-auditor`) is unchanged and remains the recommended path for most users. Vendoring is an additional path for self-contained integration into the author's own CC-based agent projects.
- Python utility layer unchanged. 29-test suite continues to pass.
- The untracked recipe drafts under `recipes/` (clinicaltrials, github-refs, sec-edgar) remain unchanged. The recipe/preset design direction was reassessed during v1.3 office-hours as low-value given the primarily-lawyer audience — deferred indefinitely.

---

## [1.2.0] — 2026-04-23

### Added
- **`us-law` verifier** (authority 0.9): verifies US legal citations against Cornell Law School's Legal Information Institute (U.S.C., C.F.R.) and CourtListener's free v4 REST API (SCOTUS opinions by reporter or case name). Catches fabricated U.S.C./C.F.R. sections, non-existent SCOTUS reporter citations, real cases with mismatched holdings.
- **`uk-law` verifier** (authority 0.9): verifies UK legal citations against BAILII (case law via neutral citations — UKSC, UKHL, UKPC, EWCA Civ/Crim, EWHC, UKUT) and legislation.gov.uk (statutes). Handles pre-2001 back-assigned neutral citations (e.g., Donoghue v Stevenson `[1932] UKHL 100`).
- **`eu-law` verifier** (authority 0.9): verifies EU legal citations against EUR-Lex via CELEX numbers. Includes named-act lookup table for GDPR, DSA, DMA, AI Act, eIDAS, MiCA, NIS 2, DSM Copyright Directive, Data Act. Catches fabricated CELEX numbers, non-existent articles, real regulations with wrong attributed content.
- **WebSearch fallback protocol** in all three new verifiers: when canonical WebFetch is permission-denied, blocked by anti-bot interstitials (BAILII Anubis), or returns a JS-rendered shell with empty body (EUR-Lex), verifiers fall back to domain-scoped WebSearch (`site:law.cornell.edu`, `site:bailii.org`, `site:eur-lex.europa.eu`) before returning `unknown`. EU verifier also retries the ELI alias (`/eli/reg/<year>/<n>/oj/eng`) before WebSearch.
- **Project-level `.claude/settings.json`** with WebFetch allowlist for the new domains (law.cornell.edu, courtlistener.com, bailii.org, legislation.gov.uk, eur-lex.europa.eu) so subagents have first-class access without per-call permission prompts.

### Validation
- E2E: `fixtures/v1.2-global-legal.md` — 6-claim English-language briefing mixing US, UK, and EU jurisdictions with three real and three fabricated citations. **6/6 correctly classified** (3 verified, 3 contradicted). Annotated output preserved at `fixtures/v1.2-global-legal.audited.md`.
- WebSearch fallback proven necessary in 4 of 6 claims (Cornell LII denied, BAILII Anubis-blocked, EUR-Lex empty body) — confirms the fallback is not a defensive nicety but a real-world primary path.

### Notes
- Recipes (`clinicaltrials`, `github-refs`, `sec-edgar`) explored during v1.2 design were deferred to v1.3 along with the broader question of how to ship and label community-contributable verifiers. See v1.3 roadmap.
- All three new verifiers use only free, no-authentication public sources. No API keys required.
- Python utility layer unchanged. 29-test suite continues to pass.
- Rationales remain Korean per v1.0 convention.

---

## [1.1.0] — 2026-04-22

### Added
- **`scholarly` verifier** (authority 0.9): verifies academic and scientific citations against free public APIs without any authentication.
  - DOI lookup via CrossRef (`api.crossref.org/works/<DOI>`)
  - arXiv ID lookup via `arxiv.org/abs/<id>`
  - PMID lookup via PubMed E-utilities (`eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi`)
  - Structured journal citation search via CrossRef title+journal+year filter
  - Catches fabricated DOIs, nonexistent PMIDs, real DOIs with wrong metadata (authors/year/journal mismatch)
- **`wikipedia` verifier** (authority 0.7): verifies general-knowledge facts (historical events, biographical details, founding years, treaty dates, organization leadership) against Wikipedia's REST summary API.
  - English Wikipedia primary, Korean Wikipedia for Korean-locale subjects
  - Summary API first; full-article WebFetch when summary lacks the specific detail
  - Catches fabricated entities (no such Wikipedia page), factually wrong dates, misattributed quotes
- **README bilingual overhaul**: English README now explicitly demonstrates non-Korean, non-legal domains (medical, financial, scientific, historical, journalistic). The Live Example section uses an English-language briefing to demonstrate the pipeline for English-only readers; a separate "End-to-End Validation" note preserves the Korean legal 10/10 result as evidence.
- Bundled Verifiers table now lists four verifiers with their patterns, authorities, and mechanisms.
- Verification Boundary table switched to international English examples (Miranda, GDPR, HIPAA, Westphalia, Lancet) so the table communicates to an English audience first.

### Changed
- Community-verifier ideas list updated to exclude what was shipped (scholarly, wikipedia, pubmed) and include new candidates (`clinicaltrials`, `github-refs`, expanded legal-region coverage).

### Notes
- All new verifiers use only free, no-authentication public APIs. No API keys required for any bundled verifier.
- New verifiers are pure skill files; no Python utility changes. The 29-test Python suite continues to pass unchanged.

---

## [1.0.0] — 2026-04-22

### Highlights
- 첫 stable 릴리스.
- 실사용 E2E 테스트에서 **10개 claim 중 10개 정확 분류** (korean-law 7/7, general-web 2/2 + 추측 문장 1건 정상 미추출).
- Hallucination 감지 증거 5건 확인:
  - 존재하지 않는 조문 2건(`게임산업진흥법 제300조`, `청소년보호법 제88조`) — MCP의 "조문 내용을 찾을 수 없습니다" 응답을 부재 신호로 해석
  - 존재하지 않는 판례 사건번호 1건(`대법원 2099다99999`)
  - 실존 판례이나 주제 불일치 1건(`대법원 2023다302036`의 실제 쟁점은 반사회적 법률행위, 주장은 확률형 아이템)
  - 일반 사실 오류 1건(게임시장 성장률 `15%` 주장, 실제 `3.4%`)

### Added (v1 스코프)
- Claude Code 플러그인 구조: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `/audit` 슬래시 커맨드.
- Primary orchestration skill (`citation-auditor`): 마크다운 청킹 → claim 추출 → verifier 라우팅 → Task tool 서브에이전트 디스패치 → verdict aggregation → 배지 삽입 및 Audit Report 렌더.
- 번들 verifier skill 2종:
  - `korean-law` (authority 1.0): Korean-law MCP 기반 법령 조/항/호 원문 비교, 판례 사건번호 존재 확인 + 검색 결과 제목 기반 쟁점 불일치 탐지.
  - `general-web` (authority 0.5): WebSearch로 후보 URL 탐색 → WebFetch로 본문 조회 → 비교.
- Python 결정론 유틸(`citation_auditor`): 마크다운 AST 기반 청킹과 역순 offset 배지 삽입(`chunking.py`, `render.py`), verdict 가중치 합의(`aggregation.py`), 한국 법률 인용 파싱(`korean_law.py`).
- 3rd-party verifier skill 작성 가이드: [skills/README.md](skills/README.md).
- Day 1 Korean-law MCP 해상도 스파이크 문서: [docs/day1-mcp-resolution.md](docs/day1-mcp-resolution.md).

### Principles
- **CC-native**: 별도 Anthropic API 키/Tavily 키/LLM provider 설정 없음. CC가 이미 실행 중인 Claude가 모든 추론 수행. Privacy는 CC 환경의 `ANTHROPIC_BASE_URL`을 자동 상속.
- **기존 파이프 무침입**: `md-to-docx.py` 등 소비 측 스크립트 수정 0줄. 출력은 순수 마크다운.
- **감사 대상 경계**: 검증 가능한 사실 주장과 인용만 감사. 예측/전망/의견/풍문은 기본적으로 추출하지 않음.
- **단방향**: writing-agent로의 피드백 루프는 이 릴리스에 포함하지 않음.

### Known limitations
- Privacy 모드(`ANTHROPIC_BASE_URL` 로컬 엔드포인트 + `local_only`) 실환경 E2E 검증은 v1.x 과제. 코드 경로 자체는 준비돼 있음.
- 판례 원문 비교(판시사항/판결요지 full-text 대조)는 `get_precedent_text`의 실패율이 높아 자동 검증하지 않음. 사건번호 존재 확인 + 검색 결과 제목 기반 주제 불일치 탐지까지만 수행.
- `LAW_ID_LOOKUP` 하드코드 테이블은 `민법`, `개인정보 보호법`만 확정. 그 외 법령은 `search_law` fallback 경로로 해결.
- 마켓플레이스 frontmatter 스키마에서 custom 필드(`patterns`, `authority`) 경고가 표시됨(런타임 동작에는 무관). `metadata:` 블록 이전은 후속 작업.

---

## [0.1.3] — 2026-04-22

### Fixed
- `general-web` verifier가 `WebSearch`로 후보 URL을 먼저 찾도록 skill 지시를 명시화. 이전에는 서브에이전트가 URL을 추측에 의존 → 위키피디아 같은 뻔한 소스만 성공하고 한국 게임 시장 통계처럼 특정 출처가 필요한 claim은 조기 실패.
- 게임시장 `15%` 성장 주장 같은 일반 사실 검증이 이제 `3.4%` 공식 통계와 비교해 `contradicted`로 정확히 판정.

## [0.1.2] — 2026-04-22

### Fixed
- `korean-law` Protocol A 규칙 재정비: MCP의 "조문 내용을 찾을 수 없습니다" 응답을 **명시적 부재 신호**로 해석해 `contradicted` 반환(이전에는 일반 실패와 함께 `unknown`으로 처리해 hallucination을 놓침).
- `general-web`: 모든 후보 페이지 fetch 시도 후에만 `원문 조회 실패` 반환. 일부만 실패해도 성공한 페이지 기반으로 판단하도록.
- "원문 조회 실패" 문구를 **실제 fetch 실패에만** 예약. 증거 혼재/불충분 상황에서는 상황을 설명하는 rationale 사용.

## [0.1.1] — 2026-04-22

### Changed
- `plugin.json`·`pyproject.toml` 버전을 0.1.0에서 0.1.1로 bump하여 CC 플러그인 캐시 재다운로드 강제. CC는 동일 버전 문자열에 대해 재다운로드하지 않는 특성이 있음.

## [0.1.0] — 2026-04-21

### Added
- 초기 스캐폴드.
- CC-native 아키텍처 확정: Skill이 primary driver, Python은 결정론 유틸, Plugin이 wrapper.
- Week 1~3 작업: Python 유틸(`chunking`, `render`, `aggregation`, `korean_law`) 및 테스트, verifier skill 2종 초안, 주요 법령 인용 파싱, 판례 검색 결과 title 기반 쟁점 불일치 탐지, Evidence 필드 일관성 규칙, README Prerequisites 및 감사 대상 범위 섹션.
- `.claude-plugin/marketplace.json` 추가: 본 저장소를 단일 플러그인 마켓플레이스로 subscribe 가능.

### Notes
- 공용 마켓플레이스(`claude-plugins-official`) 제출은 하지 않음. GitHub 저장소 직접 subscribe 경로만 운영.
- 설치: `/plugin marketplace add kipeum86/citation-auditor` → `/plugin install citation-auditor@citation-auditor`.
