# citation-auditor

🌐 **언어**: [English](../../README.md) | **한국어**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](../../CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](../../LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-orange.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Tests](https://img.shields.io/badge/tests-29%2F29_passing-brightgreen.svg)](../../tests/)

> **⚠️ 결과물은 AI가 생성한 감사 기록입니다. 반드시 자격 있는 전문가의 검토를 거친 뒤 사용하세요.** 이 플러그인은 의심스러운 인용과 사실 주장을 표시해 줄 뿐, 법률 전문가나 도메인 전문가의 판단을 대체하지 않습니다. `✅` 배지는 *"반박 증거를 찾지 못함"*을 의미하지 *"완전히 맞다는 확정"*이 아닙니다. `⚠️`와 `❓`는 **반드시 사람이 확인**해야 하는 표식입니다.

**citation-auditor**는 Claude Code 용 **확장형 팩트체크·인용 감사 레이어**입니다. AI 에이전트가 생성한 마크다운 출력에서 사실 주장을 추출하고, 도메인별 verifier 서브에이전트에게 검증을 위임한 뒤, 원본 마크다운에 배지(✅ / ⚠️ / ❓)와 `Audit Report`를 덧붙여 돌려줍니다.

인용 정확도가 중요한 모든 AI 에이전트에서 사용하도록 설계했습니다 — **법률 의견서, 의료 요약, 금융 분석, 학술 브리프, 언론 기사 초안**. 기본 번들 verifier는 한국 법률(Korean-law MCP 기반)과 일반 웹 소스를 다루며, verifier 인터페이스는 서드파티 확장이 가능하도록 열려 있습니다.

**"AI 신뢰 인프라"** 시리즈의 일부 — AI에 보내기 *전* redaction을 담당하는 `document-redactor`와 **짝을 이루는 "AI에서 받은 후" 검증 레이어**입니다.

---

## 📌 플랫폼 호환성

> 이 플러그인은 **Claude Code 전용**입니다. 아래 환경에서는 **작동하지 않습니다**:
> - Claude Desktop 앱
> - claude.ai 웹 인터페이스
> - Anthropic API (SDK 직접 사용)
> - 다른 AI 코딩 도구 (Cursor, Zed, Windsurf 등)

Claude Code 고유 기능에 의존하기 때문입니다 — frontmatter 기반 skill 포맷, 슬래시 커맨드, 서브에이전트 디스패치용 Task tool, 유틸 호출용 Bash tool, 세션 수준 MCP 서버 통합. 이 요소들은 다른 환경으로 이식되지 않습니다.

Python 유틸 레이어(`python -m citation_auditor chunk|render|aggregate|korean_law …`)는 어느 환경에서든 CLI로 호출할 수 있지만, Claude Code 측 오케스트레이션이 없으면 end-to-end 검증 흐름은 돌아가지 않습니다.

---

## 📖 목차

- [문제 정의](#문제-정의)
- [주요 기능](#주요-기능)
- [지원하지 않는 기능](#지원하지-않는-기능)
- [작동 원리](#작동-원리)
- [번들 verifier](#번들-verifier)
- [빠른 시작](#빠른-시작)
- [실제 예시](#실제-예시)
- [감사 대상 범위](#감사-대상-범위)
- [프라이버시 및 데이터](#프라이버시-및-데이터)
- [자기 verifier 만들기](#자기-verifier-만들기)
- [개발 환경](#개발-환경)
- [프로젝트 구조](#프로젝트-구조)
- [요구사항](#요구사항)
- [로드맵](#로드맵)
- [라이선스](#라이선스)

---

## 문제 정의

실무에 쓰는 AI 에이전트는 **그럴듯해 보이지만 조작된 인용**을 모든 도메인에서 일상적으로 생성합니다:

- **법률.** 의견서가 `민법 제103조`를 인용하면서 실제 조문에 없는 내용을 규정한다고 서술. `대법원 2023다12345` 같은 판례 번호가 존재하지 않거나, 존재해도 인용된 판시 내용이 실제 판례와 무관. 컴플라이언스 메모가 `청소년보호법 제88조`를 인용하지만 해당 법에 88조 자체가 없음(총 64조까지).
- **의료.** 리뷰 논문이 *"Lancet 2019;394:1234-45"*을 인용하는데 실제로 출판된 적 없는 논문. 진료 지침이 *"WHO 가이드라인"*의 권고라며 실제 해당 가이드라인에 없는 내용을 서술.
- **금융.** 리서치 브리프가 *"2023년 반도체 시장 15% 성장"*이라 쓰는데 공식 SEMI 통계는 3.4%. 실사 메모가 *"SEC Rule 10b5-1(c)(2)(iv)"*를 인용하지만 해당 규칙은 (iii)까지만 존재.
- **학술·역사.** 논문이 *"Einstein, 1953"* 출처로 발언을 인용하는데 검증 가능한 근거 없음. 역사 브리프가 *"베스트팔렌 조약은 1653년에 체결"*이라고 서술(실제: 1648년).
- **저널리즘.** 분석 기사가 *"2023년 MIT 연구에 따르면"*이라고 쓰는데 해당 연구가 존재하지 않음. 존재하지 않는 Pew Research 여론조사 결과 인용.

현재는 전문가가 문서 1건당 10~30분씩 직접 원문 대조로 체크합니다. **citation-auditor는 이 과정을 ~5분으로 압축**합니다 — 의심 구간을 `⚠️` / `❓` 배지로 먼저 표시해 주면, 리뷰어는 **사람의 판단이 필요한 부분에만 집중**할 수 있습니다.

---

## 주요 기능

- **추출**: AI 마크다운 출력에서 검증 가능한 사실 주장과 인용을 파싱
- **라우팅**: 각 claim을 도메인에 맞는 verifier skill로 분배
- **병렬 디스패치**: Claude Code의 Task tool로 verifier 서브에이전트 병렬 실행
- **판정 집계**: authority 가중치 기반 합의로 최종 verdict 결정
- **재방출**: 원본 마크다운에 인라인 배지 + 문서 끝 `## Audit Report` 섹션 삽입
- **파이프라인 무침입**: 기존 소비 측 스크립트(`md-to-docx.py` 등) 수정 0줄

## 지원하지 않는 기능

- **법률 자문, 위험 평가, 전략 권고** — 감사 결과는 증거 기반 팩트체크일 뿐
- **추측·전망·의견·풍문 검증** — *"업계 관계자에 따르면 규제가 완화될 전망"* 같은 문장은 설계상 감사 대상에서 제외
- **판례 본문 심층 비교** — 판례 인용은 사건번호 존재 + 검색 결과 제목 기반 쟁점 불일치 탐지까지. 전문 판시사항 분석은 향후 버전 이연
- **법리 추론 평가** — 정확한 인용이 실제로 논증을 지지하는지는 대상 밖
- **자동 재작성** — verdict는 주석일 뿐. 의심 구간 수정은 사람 또는 상위 writing agent의 몫

---

## 작동 원리

**하나의 Claude Code 플러그인에 세 레이어가 감싸져 있습니다:**

```
┌──────────────────────────────────────────────────────────────┐
│  Plugin  .claude-plugin/plugin.json + marketplace.json        │
│          commands/·skills/ 경로를 Claude Code에 선언          │
└──────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴──────────────────────┐
        ▼                                            ▼
┌───────────────────────┐              ┌──────────────────────────┐
│  Skills   (주 드라이버)│              │  Python  (결정론 유틸)    │
│                       │  bash 호출   │                          │
│  citation-auditor ────┼─────────────►│  chunk / aggregate /     │
│  verifiers/*          │   stdout     │  render / korean_law     │
└───────────────────────┘              └──────────────────────────┘
        │
        │ Task tool 디스패치
        ▼
┌─────────────────────────────────────┐
│  Verifier 서브에이전트 (병렬)         │
│  korean-law  → Korean-law MCP       │
│  general-web → WebSearch + WebFetch │
└─────────────────────────────────────┘
```

- **Skill이 오케스트레이션 주도.** `citation-auditor` skill이 Claude를 지휘해 청킹 → claim 추출 → verifier 라우팅 → Task 기반 병렬 검증 → 집계 → 렌더링까지 순차 진행.
- **Python은 결정론 작업만 담당.** 마크다운 AST 청킹, 역순 offset 배지 삽입, verdict 가중치 합의, pydantic 스키마 검증, 한국 법률 인용 파싱. LLM 호출/외부 API 호출 0건.
- **Verifier = skill 파일.** 각 verifier는 독립된 `skills/verifiers/<name>/SKILL.md`. frontmatter에 `patterns` + `authority` 선언, 본문에 "claim을 받아 어떻게 검증하고 verdict JSON을 리턴할지" 명세. Claude가 Task tool 서브에이전트 디스패치를 통해 skill 로드.

**CC-native 설계 원칙:** 별도 Anthropic API 키 불필요, Tavily 키 불필요, LLM provider 설정 불필요. 당신 Claude Code 세션에서 이미 실행 중인 Claude 인스턴스가 모든 추론을 수행합니다. Privacy 설정(예: `ANTHROPIC_BASE_URL`로 로컬 엔드포인트 라우팅)은 자동 상속됩니다.

---

## 번들 verifier

| Verifier | Authority | Pattern 매칭 | 메커니즘 |
|---|:---:|---|---|
| **`korean-law`** | 1.0 | 제N조, 주요 법령명, 판례번호 | Korean-law MCP로 조문 원문 비교 (조/항/호 단위) + 판례 사건번호 존재 확인 + 검색 결과 제목 기반 쟁점 불일치 탐지 |
| **`general-web`** | 0.5 | `.*` (모든 claim fallback) | WebSearch로 상위 3개 권위 있는 URL 선정 → WebFetch로 본문 수집 → LLM 기반 claim 판정 |

**Verdict 집계 정책:** 하나의 claim에 여러 verifier가 매치되면 **authority 가중치**가 높은 verdict가 우선. 동일 authority에서 판정이 엇갈리면 `❓`(충돌 신호, 억지 verdict 금지) 반환.

---

## 빠른 시작

### 사전 요구사항

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 설치 및 정상 동작
- Python 3.11+ 와 [`uv`](https://docs.astral.sh/uv/)가 `PATH`에 있어야 함
- (`korean-law` verifier 사용 시) Korean-law MCP 서버가 Claude Code 세션에 연결돼 있어야 함
- (`general-web` verifier 사용 시) WebFetch + WebSearch가 세션에서 사용 가능해야 함

### 설치

Claude Code 세션 안에서:

```
/plugin marketplace add kipeum86/citation-auditor
/plugin install citation-auditor@citation-auditor
```

scope 선택 프롬프트가 뜨면 **User scope** 선택. User scope는 `~/.claude/` 에 설치되어 모든 Claude Code 세션에서 자동으로 활성화되며, **당신의 프로젝트 레포에는 아무것도 기록되지 않습니다**(레포 오염 0건 원칙).

### 리로드

```
/reload-plugins
```

### 마크다운 파일 감사

```
/citation-auditor:audit path/to/opinion.md
```

출력은 원본 마크다운과 동일하되, 감사 대상 문장 끝마다 `**[✅ verifier-name]**` / `**[⚠️ verifier-name]**` / `**[❓ verifier-name]**` 배지가 삽입되고 문서 끝에 `## Audit Report` 섹션이 추가됩니다 — 각 claim의 verdict, rationale, evidence 포함.

### 업데이트

```
/plugin update citation-auditor@citation-auditor
```

---

## 실제 예시

**입력** — AI가 초안한 법률 메모, 사실 인용과 환각 인용이 섞여 있음:

```markdown
계약의 유효성 판단에 있어 민법 제103조는 선량한 풍속 기타 사회질서에
위반한 사항을 내용으로 하는 법률행위는 무효로 한다고 규정한다.

게임산업진흥에 관한 법률 제300조 제5항은 확률형 아이템의 개별 확률을
소수점 다섯 자리까지 공시할 것을 의무화한다고 규정한다.

대법원 2023다302036 판결은 확률형 아이템 소비자 보호 의무 위반 시
사업자의 손해배상 책임을 인정한 선례이다.

2023년 한국 게임 시장 규모는 약 22조 원으로, 전년 대비 15% 성장하였다.
```

**`/citation-auditor:audit` 실행 후 주석이 달린 출력:**

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

실전 E2E 테스트에서, 사실 인용과 환각 인용이 섞인 10개 claim짜리 게임·법률 의견서에 대해 **10/10 정확 분류**. 환각 5건 모두 포착(존재하지 않는 조문 2건, 존재하지 않는 사건번호 1건, 주제 불일치 판례 1건, 성장률 오류 1건 — 마지막은 정확한 수치까지 rationale에 제시).

---

## 감사 대상 범위

citation-auditor는 **검증 가능한 사실 주장과 인용**만 감사합니다. 다음은 의도적으로 감사 대상에서 제외됩니다:

| 분류 | 예시 | 감사? |
|---|---|:---:|
| 조문 인용 | "민법 제103조는 ~라고 규정한다" | ✅ 감사 |
| 판례 인용 | "대법원 2023다302036 판결" | ✅ 감사 |
| 사실 주장 | "2023년 게임 시장은 22조 원이다" | ✅ 감사 |
| 역사적 사실 | "블리자드는 1991년 설립되었다" | ✅ 감사 |
| 전망·예측 | "2026년 하반기에 규제가 완화될 전망이다" | ❌ 미감사 |
| 업계 풍문 | "업계 관계자에 따르면 ~" | ❌ 미감사 |
| 의견·가치판단 | "이 접근은 합리적이다" | ❌ 미감사 |
| 법리 추론 | "따라서 본 조항은 무효이다" (인용 조문으로부터의 결론) | ❌ 미감사 |

감사되지 않은 문장은 배지가 붙지 않습니다. 사람이 직접 검토해야 합니다.

---

## 프라이버시 및 데이터

- **별도 API 키 없음.** 플러그인은 당신 Claude Code 세션의 Anthropic 인증과 구성된 `ANTHROPIC_BASE_URL`(로컬 Ollama 엔드포인트 등 포함)을 자동 상속합니다.
- **텔레메트리 없음.** 사용 데이터 수집이나 외부 보고 기능이 없습니다.
- **웹 조회는 번들 verifier 경로로만.** `general-web` verifier가 Claude Code 세션의 WebSearch와 WebFetch를 사용합니다. 세션에서 해당 도구가 제한·차단되면 verifier는 `❓`를 반환할 뿐 다른 경로로 본문을 유출하지 않습니다.
- **한국 법률 조회**는 세션에 구성된 Korean-law MCP 서버로 전달됩니다. 쿼리 내용의 처리 방식은 해당 MCP 구현에 따릅니다.
- **`local_only` 모드.** 두 번들 verifier 모두 `local_only` 플래그를 지원합니다 — 설정 시 모든 외부 호출을 건너뛰고 `❓ "로컬 전용 모드"`로 반환합니다.

민감 문서(비밀·특권 정보, PHI, PII)를 처리할 때는 감사 실행 **전에** Claude Code 세션의 data retention과 base URL 설정을 조직 정책에 맞게 구성해야 합니다. 플러그인은 그 설정을 덮어쓰거나 우회하지 않습니다.

Anthropic 공식 참조:
- [Claude Code 데이터 사용](https://docs.anthropic.com/en/docs/claude-code/data-usage)
- [Commercial data retention](https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)

---

## 자기 verifier 만들기

Verifier는 `skills/verifiers/<your-name>/SKILL.md` 하나짜리 skill 파일이며 아래 frontmatter를 가집니다:

```yaml
---
name: your-verifier-name
description: 검증 대상과 방식을 한 줄로 요약
patterns:
  - "정규식 패턴 1"
  - "정규식 패턴 2"
authority: 0.7          # 0.0 ~ 1.0 사이
disable-model-invocation: true
---
```

본문에는 검증 프로토콜을 씁니다 — claim JSON 수신 방식, 사용할 도구(MCP, WebFetch, 또는 Claude Code 서브에이전트가 쓸 수 있는 모든 도구), `{label, rationale, supporting_urls, authority}` 형태의 verdict JSON 반환 규칙.

전체 규격(JSON 입출력 계약 포함)은 [skills/README.md](../../skills/README.md) 참조. 완성된 레퍼런스 구현은 번들 `korean-law` verifier: [skills/verifiers/korean-law/SKILL.md](../../skills/verifiers/korean-law/SKILL.md).

**커뮤니티에서 시도해볼 만한 도메인 verifier:**
- `us-law` (Cornell LII, CourtListener)
- `pubmed` (PubMed E-utilities MCP)
- `eu-law` (EUR-Lex)
- `case-law-uk` (BAILII)
- `sec-filings` (EDGAR MCP)
- `financial-stats` (FRED, 한국은행 API)

---

## 개발 환경

```bash
git clone https://github.com/kipeum86/citation-auditor
cd citation-auditor
uv sync --group dev
uv run pytest
```

29개 테스트가 Python 유틸 레이어(청킹, 렌더, 집계, 한국 법률 인용 파싱)를 커버합니다. Skill은 LLM 오케스트레이션과 tool dispatch가 얽혀 있어 **실제 Claude Code 세션에서 E2E로 검증**합니다.

CLI 유틸 직접 스모크 테스트:

```bash
echo -e "Alpha.\n\n민법 제103조에 따른 법률행위는 무효이다." > /tmp/test.md
uv run python -m citation_auditor chunk /tmp/test.md --max-tokens 3000
uv run python -m citation_auditor korean_law parse "민법 제103조"
```

---

## 프로젝트 구조

```
citation-auditor/
├── .claude-plugin/
│   ├── plugin.json               # Claude Code 플러그인 매니페스트
│   └── marketplace.json          # 단일 플러그인 마켓플레이스 선언
├── commands/
│   └── audit.md                  # /audit 슬래시 커맨드 (→ citation-auditor skill)
├── skills/
│   ├── README.md                 # 서드파티 verifier 작성 가이드
│   ├── citation-auditor/
│   │   └── SKILL.md              # 주 오케스트레이션 skill
│   └── verifiers/
│       ├── general-web/SKILL.md  # WebSearch + WebFetch verifier
│       └── korean-law/SKILL.md   # Korean-law MCP verifier
├── citation_auditor/             # Python 유틸 패키지 (결정론 전용)
│   ├── __main__.py               # CLI 진입점: chunk|aggregate|render|korean_law
│   ├── chunking.py               # 마크다운 AST 청킹, 문단 오버랩
│   ├── render.py                 # Marko 기반 배지 삽입 + Audit Report
│   ├── aggregation.py            # Authority 가중 verdict 합의
│   ├── models.py                 # Pydantic 스키마 (Claim, Verdict 등)
│   ├── settings.py               # AuditSettings (API 키 없음)
│   └── korean_law.py             # 인용 파싱, 항/호 추출, 사건번호 정규화
├── docs/
│   ├── day1-mcp-resolution.md    # Korean-law MCP 해상도 스파이크 노트
│   └── ko/
│       └── README.md             # 이 문서 (한국어 미러)
├── tests/                         # 29개 pytest 케이스
├── fixtures/                      # 합성 테스트 의견서
├── CHANGELOG.md
├── LICENSE                        # Apache License 2.0
├── pyproject.toml                 # 런타임 pydantic + marko, dev pytest
└── README.md                      # 영문 정본
```

---

## 요구사항

- Claude Code (최신 버전 권장)
- Python 3.11+
- `uv` (환경 관리)
- 선택: Korean-law MCP 서버 (`korean-law` verifier용)
- 선택: Claude Code 세션에서 WebFetch + WebSearch 활성화 (`general-web` verifier용)

런타임 Python 의존성은 의도적으로 최소 — `pydantic`과 `marko`뿐. HTTP 클라이언트, 외부 SDK, LLM provider 의존성 0건.

---

## 로드맵

**v1.0 (출시 — 2026-04-22)**
- Skill-primary 아키텍처와 Python 결정론 유틸
- 번들 `korean-law`, `general-web` verifier
- 서드파티 verifier 확장 계약
- 마크다운-in/마크다운-out, 하류 파이프라인 수정 0
- 사실/환각 혼합 의견서 실전 E2E 10/10 정확 분류

**v1.x (계획)**
- 생성 직후 자동 감사를 위한 `SubagentStop` hook
- Feedback loop 모드: `⚠️` / `❓` claim을 상위 writing agent에 재작성 요청으로 반환
- MCP tool form: `verify_claim`을 MCP tool로 노출, CC 호환 클라이언트 누구나 호출
- 로컬 Ollama 엔드포인트 대상 Privacy E2E 실환경 검증
- Claude Code의 기존 provider 추상화를 통한 OpenAI / 기타 provider 지원
- Frontmatter `metadata:` 블록 이전 (스키마 compliance)

릴리스 노트: [CHANGELOG.md](../../CHANGELOG.md)

---

## 라이선스

Apache License 2.0. [LICENSE](../../LICENSE) 참조.
