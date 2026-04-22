# Changelog

All notable changes to citation-auditor are documented here. This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
