# citation-auditor

AI 에이전트가 뱉은 마크다운에서 사실 주장을 뽑아 **pluggable verifier**로 검증하고, 본문에 배지(✅/⚠️/❓) + 끝에 Audit Report를 붙여 돌려주는 Claude Code 플러그인.

"AI 신뢰 인프라" 시리즈의 후위 레이어. `document-redactor`가 AI에 **보내기 전** redaction을 맡는다면, `citation-auditor`는 AI에서 **받은 후** verification을 맡는다.

## 어떤 문제를 푸나

AI 에이전트 출력물의 환각된 인용 — "민법 제103조에 X라고 규정되어 있다"인데 실제 103조는 다른 내용, "대법원 2023다12345"인데 실제로는 존재하지 않는 번호 — 를 자동으로 포착한다. 인간이 docx 검토 단계에서 10-30분씩 수동 체크하던 일을, 플러그인이 미리 의심 구간을 ⚠️/❓로 표시해 검토를 5분으로 압축.

법무 전용 아님. `general-web` + `korean-law` 두 verifier가 번들돼 있지만, verifier는 **skill 파일 단위**로 확장 가능하다. 의료, 금융, 과학, 역사 — 사실 주장 검증이 필요한 임의의 도메인에 새 verifier skill을 붙일 수 있다.

## 아키텍처 (v1)

**3-레이어 구조:**

```
┌──────────────────────────────────────────────────────────┐
│  Plugin (.claude-plugin/plugin.json)                      │
│  — commands/, skills/ 경로를 Claude Code에 선언            │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌──────────────────┐              ┌────────────────────┐
│ Skills (primary) │              │ Python utils       │
│                  │  bash call   │ (deterministic)    │
│ citation-auditor │─────────────▶│ chunk / aggregate /│
│ verifiers/*      │   stdout     │ render             │
└──────────────────┘              └────────────────────┘
```

- **Skills가 주 드라이버.** `citation-auditor` 스킬이 Claude를 지휘해 claim 추출 → verifier 라우팅 → Task tool로 서브에이전트 디스패치 → 결과 집계 → 최종 마크다운 방출.
- **Python은 결정론 유틸만.** 마크다운 청킹, AST 기반 배지 삽입, verdict 가중치 aggregation, pydantic 스키마 검증. LLM 호출/외부 API 호출 0건.
- **Verifier = skill 파일.** 각 verifier는 `skills/verifiers/<name>/SKILL.md`. frontmatter에 `patterns` + `authority` 선언, 본문에 "claim 받아 어떻게 검증하고 verdict JSON 리턴할지" 명세. Claude가 Task tool로 서브에이전트 디스패치하면서 해당 skill을 로드.

**CC-native 원칙:** Anthropic API 키, Tavily 키, 별도 LLM provider 설정 — 전부 없음. Claude Code가 이미 돌리고 있는 Claude 인스턴스가 모든 추론 수행. Privacy 모드는 `ANTHROPIC_BASE_URL` 등 CC 환경 자체 설정을 자동 상속.

## Prerequisites

- Claude Code가 설치되어 있고 `/plugin install`을 실행할 수 있어야 함
- Python 3.11+와 `uv`가 로컬 환경에 있어야 함
- `korean-law` verifier를 쓰려면 Korean-law MCP가 현재 Claude Code 세션에 연결돼 있어야 함
- `general-web` verifier를 쓰려면 WebFetch가 가능한 세션이어야 함
  외부 원문 조회가 금지된 환경이면 `local-only` 모드로 돌려 `❓` 판정을 받도록 운영 가능

## 설치

```bash
/plugin install github:<user>/citation-auditor
```

처음 실행 시 Python 유틸 의존성(`pydantic`, `marko`) 자동 설치. 별도 API 키 불필요.
설치 직후 `/audit` 명령이 보이지 않으면 Claude Code 세션을 한 번 재시작한 뒤 다시 확인.

## 사용

```
/audit <file.md>
```

- 마크다운 파일 하나 받음
- Claude가 청킹 → claim 추출 → verifier 라우팅 → 병렬 검증 → aggregate → render
- 본문 문장 끝에 `**[✅ general-web]**` / `**[⚠️ korean-law]**` / `**[❓ general-web]**` 배지 삽입
- 문서 끝에 `## Audit Report` 섹션으로 claim별 rationale + 참고 소스

## Verification Boundary

이 플러그인은 **검증 가능한 사실 주장과 인용**을 감사한다. 다음처럼 예측, 의견, 풍문, 전언 위주의 문장은 기본적으로 추출하지 않는다.

- `업계 관계자에 따르면 규제가 완화될 전망이다`
- `향후 판례가 바뀔 가능성이 높다`
- `회사 측은 시장 반응이 좋을 것으로 본다`

이런 문장은 사실상 "맞다/틀리다"를 즉시 대조할 공적 원문이 없기 때문이다. 반대로 아래처럼 구체적 사실이 들어 있으면 감사 대상이다.

- `개인정보 보호법 제15조 제1항 제2호는 법률에 특별한 규정이 있거나 ... 불가피한 경우를 규정한다`
- `대법원 2023다302036 판결이 존재한다`

판례 검증도 경계를 둔다. `korean-law` verifier는 사건번호 존재 여부와 검색 결과 제목 기준의 **쟁점 불일치**는 잡아내지만, 판결 원문 전체를 읽어 세부 판시를 자동 확정하지는 않는다. 사건번호는 맞지만 쟁점이 비슷하거나 애매한 경우에는 `❓`로 두고 원문 확인을 권장한다.

Evidence 표기도 source 종류에 맞춰 다르게 보인다.

- 법령 조문을 실제로 조회한 경우: `law.go.kr/법령/<법령명>/<조>`
- 판례 사건번호를 검색 결과로 확인한 경우: `law.go.kr 판례 검색 결과 ID <n> (전문 제공 여부가 일정하지 않을 수 있습니다.)`

즉, 판례 evidence가 링크가 아니라고 해서 조회를 안 한 것이 아니라, 현재 MCP에서 안정적인 전문 링크를 항상 주지 않기 때문이다.

## 번들된 verifier (v1)

| Verifier | Authority | Patterns | 메커니즘 |
|---|---|---|---|
| `korean-law` | 1.0 | `제N조`, 주요 법령명, 판례번호 패턴 | 법령은 조/항/호 원문 비교, 판례는 사건번호 확인 + 검색 제목 기준 쟁점 불일치 탐지 |
| `general-web` | 0.5 | `.*` (fallback) | WebFetch로 관련 페이지 최대 3개 조회 후 LLM 판정 |

하나의 claim에 여러 verifier가 매치되면 **authority 가중치** 기반 합의. 동일 authority에서 판정 충돌 시 `❓` (conflict).

## 자기 verifier 만들기

`skills/verifiers/<your-name>/SKILL.md` 생성:

```yaml
---
name: your-verifier-name
description: 무엇을 검증하는지 한 줄 요약
patterns:
  - "정규식1"
  - "정규식2"
authority: 0.0
disable-model-invocation: true
---

본문: claim JSON 입력 → 도구(MCP/WebFetch/기타) 사용 검증 →
verdict JSON ({label, rationale, supporting_urls, authority}) 반환.
```

상세 규격은 [skills/README.md](skills/README.md) 참조.

## 개발 환경

```bash
uv sync --group dev
uv run pytest
```

순수 Python 유틸 테스트만 — skill 실행은 CC 세션에서 직접 돌려 확인.

```bash
echo -e "Alpha.\n\nBeta claim with numbers 2015.\n\nGamma has 민법 제103조 reference." > /tmp/test.md
uv run python -m citation_auditor chunk /tmp/test.md --max-tokens 3000
```

## 정책

- **단방향 (v1):** 검증 결과를 writing-agent에 되돌려 재작성 요청하는 feedback loop는 v1.x로 이연.
- **기존 파이프 무침입:** `md-to-docx.py` 등 소비 측 스크립트 수정 0줄. 출력 마크다운이 기존 파이프에 그대로 흘러감.
- **사실 주장 중심:** 예측, 의견, 풍문, 전망 문장은 기본적으로 감사 대상에서 제외.
- **✅ 신뢰 경고:** `✅` 배지는 "통과 신호로 보이니 1차 OK" 뜻이지 "사람 검토 불필요" 뜻 아님. `⚠️`/`❓`는 반드시 변호사/전문가가 직접 확인해야 함.

## Status

- **v1.0.0 released** (2026-04-22). 실사용 E2E 10/10 claim 정확 분류.
- 릴리스 노트: [CHANGELOG.md](CHANGELOG.md)
- v1.x 예정: `SubagentStop` hook 자동 감사, feedback loop 모드, MCP tool form, OpenAI/기타 provider, Privacy(`ANTHROPIC_BASE_URL` + `local_only`) 실환경 E2E 검증.

## License

Apache License 2.0. See [LICENSE](LICENSE).
