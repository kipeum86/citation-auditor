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

## 설치

```bash
/plugin install github:<user>/citation-auditor
```

처음 실행 시 Python 유틸 의존성(`pydantic`, `marko`) 자동 설치. 별도 API 키 불필요.

## 사용

```
/audit <file.md>
```

- 마크다운 파일 하나 받음
- Claude가 청킹 → claim 추출 → verifier 라우팅 → 병렬 검증 → aggregate → render
- 본문 문장 끝에 `**[✅ general-web]**` / `**[⚠️ korean-law]**` / `**[❓ general-web]**` 배지 삽입
- 문서 끝에 `## Audit Report` 섹션으로 claim별 rationale + 참고 소스

## 번들된 verifier (v1)

| Verifier | Authority | Patterns | 메커니즘 |
|---|---|---|---|
| `korean-law` | 1.0 | `제N조`, 주요 법령명, 판례번호 패턴 | Korean-law MCP (`get_law_text`, `search_precedents` 등) 호출 후 원문 비교 |
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
- **✅ 신뢰 경고:** `✅` 배지는 "통과 신호로 보이니 1차 OK" 뜻이지 "사람 검토 불필요" 뜻 아님. `⚠️`/`❓`는 반드시 변호사/전문가가 직접 확인해야 함.

## Status

- **v1.0 개발 중** (Week 1 완료: CC-native 스캐폴드 + 결정론 유틸 + verifier skill 초안)
- v1.x 예정: `SubagentStop` hook 자동 감사, feedback loop 모드, MCP tool form, OpenAI/기타 provider.

## License

Apache License 2.0. See [LICENSE](LICENSE).
