# citation-auditor 엔지니어링 및 설계 감사

작성일: 2026-04-27

범위: `citation-auditor` v1.4.0 코드베이스, primary skill, verifier skill 계약, CLI 유틸, DOCX sidecar 보고서 경로.

이 문서는 잘 설계된 부분을 요약하지 않는다. 변경이 필요한 지점만 기록한다.

## 1. Output Quality

### 1.1 Claim 추출 기준이 문서 설명보다 좁다

상태: 처리됨. 후속 마일스톤에서 primary skill의 추출 기준을 “verifiable factual claims and citation-bearing claims”로 넓히고, `Claim.audit_reason` 선택 필드를 추가했다.

문제: primary skill은 “factual, citation-bearing claims”만 추출하라고 지시한다. README는 사실 주장과 인용을 모두 감사한다고 설명하지만, 실제 지시는 citation-bearing에 치우쳐 있어 출처 없이 쓰인 정량·시점·고유명사 사실 주장이 누락될 수 있다.

왜 중요한가: 법률 의견서에서 위험한 문장은 항상 명시적 인용을 동반하지 않는다. “2024년부터 시행”, “시장 규모 15% 성장”, “A 기관이 고시” 같은 문장이 citation-bearing이 아니라는 이유로 빠지면 출력 품질이 사용자가 기대하는 감사 범위보다 좁아진다.

구체 수정안:

- primary skill 4단계를 “factual or citation-bearing claims”로 수정한다.
- claim extractor schema에 `audit_reason: citation | factual | quantitative | temporal`을 추가한다.
- 테스트 fixture에 “출처 없는 정량 사실 1개”를 넣고 실제 slash-command E2E 기대값에 포함한다.

### 1.2 Markdown 렌더러가 원문 보존을 보장하지 않는다

문제: `render_markdown`은 offset으로 badge를 삽입한 뒤 `marko`의 markdown renderer를 거쳐 결과를 반환한다. 이 방식은 원문 markdown의 공백, 리스트, 테이블, HTML, escaped character를 재직렬화할 수 있어 “same markdown with badges”라는 UX와 충돌할 수 있다.

왜 중요한가: 법률 문서 변환 파이프라인은 markdown의 미세한 구조가 DOCX 변환 결과에 영향을 줄 수 있다. 감사 도구가 원문 구조를 예상 밖으로 바꾸면 downstream `md-to-docx.py`류 스크립트와 충돌한다.

구체 수정안:

- `render_markdown`은 기본적으로 badge 삽입 문자열을 그대로 반환하도록 바꾼다.
- `marko.convert`는 별도 `--normalize-markdown` 옵션으로만 사용한다.
- markdown table, ordered list, inline HTML, footnote-like text를 포함한 golden test를 추가해 원문 보존을 검증한다.

### 1.3 DOCX 감사 보고서가 누락된 영역을 명시하지 않는다

상태: 처리됨. v1.4 후속 마일스톤에서 `SourceMap.omissions`와 DOCX report `Scope Notice`를 추가했다.

문제: v1.4.0 DOCX 추출은 각주, 미주, comments, 삭제된 track changes를 제외한다. 그러나 생성되는 `.audit.md` 보고서에는 “이 영역은 감사 대상에서 제외됨”이라는 범위 고지가 없다.

왜 중요한가: 법률 문서의 핵심 인용은 각주/미주에 위치하는 경우가 많다. 보고서가 조용히 본문만 감사하면 사용자는 전체 DOCX가 감사되었다고 오해할 수 있다.

구체 수정안:

- `SourceMap`에 `omissions: list[str]` 필드를 추가한다.
- `extract_docx`가 footnotes/endnotes/comments/track-changes 제외 사실을 source map에 기록한다.
- `report.py` Summary 위에 `Scope Notice` 섹션을 추가해 제외 영역을 표시한다.

### 1.4 Aggregation 결과가 하위 verifier의 강한 반박을 가릴 수 있다

문제: `aggregate_verdicts`는 authority가 가장 높은 verifier의 verdict만 최종 채택한다. 예를 들어 authority 1.0 verifier가 `unknown`을 반환하고 authority 0.5 verifier가 명확한 `contradicted`를 반환하면 최종 결과가 `unknown`으로만 남는다.

왜 중요한가: 감사 UX에서 가장 중요한 것은 “검토해야 할 위험 신호”를 놓치지 않는 것이다. 낮은 authority라도 명확한 반박 근거가 있으면 보고서에 surfaced 되어야 한다.

구체 수정안:

- 최종 verdict와 별도로 `secondary_signals`를 AggregateOutput에 추가한다.
- top authority가 `unknown`이고 lower verifier 중 `contradicted`가 있으면 최종 label은 `unknown`으로 두되 report에 `Secondary contradiction signal`을 표시한다.
- 동일 claim에 대해 `verified`와 `contradicted`가 동시에 나오면 authority 차이가 있어도 report detail에 conflict note를 남긴다.

### 1.5 Verified 항목이 긴 문서에서 reviewer attention을 과도하게 소모한다

문제: markdown render와 DOCX report 모두 verified 항목까지 전체 Audit Report에 나열한다. 긴 문서에서는 문제 없는 항목이 보고서 대부분을 차지할 수 있다.

왜 중요한가: citation-auditor의 핵심 가치는 reviewer가 `⚠️`/`❓`에 집중하게 하는 것이다. verified noise가 많으면 사람이 다시 전체 보고서를 훑게 되어 시간 절감 효과가 줄어든다.

구체 수정안:

- `report` CLI에 `--focus review` 옵션을 추가해 `contradicted`와 `unknown`만 Findings/Details 상단에 표시한다.
- verified 항목은 Summary count와 접힌 하단 섹션 또는 별도 `Verified Appendix`에만 둔다.
- markdown mode에도 `--focus review`와 대응되는 skill 옵션을 추가한다.

## 2. Token Efficiency

### 2.1 Primary skill의 aggregate JSON 예시가 매 실행마다 과하게 크다

문제: `skills/citation-auditor/SKILL.md`는 aggregate 입력 schema 전체 예시를 매번 prompt에 포함한다. v1.3에서 schema 누락을 막기 위해 추가된 내용이지만, 현재는 실행마다 상당한 고정 토큰 비용이 발생한다.

왜 중요한가: 긴 문서 감사에서는 chunk 수와 verifier subagent 호출만으로도 토큰 사용량이 커진다. 고정 prompt 토큰을 줄이면 모든 실행에서 비용이 바로 줄어든다.

구체 수정안:

- Python CLI에 `python -m citation_auditor schema aggregate-input`을 추가해 정확한 schema 예시를 출력하게 한다.
- primary skill에는 “필요 시 schema 명령을 호출하라”는 짧은 지시와 핵심 top-level key만 남긴다.
- schema 회귀를 막기 위해 `tests/test_cli.py`에 schema 출력 검증을 추가한다.

### 2.2 Verifier skill마다 JSON 계약 설명이 반복된다

문제: 각 verifier skill은 입력 형태, `local_only`, 출력 JSON, “JSON만 반환” 규칙을 반복한다. 반복 내용은 verifier 수가 늘어날수록 유지보수와 토큰 비용을 같이 증가시킨다.

왜 중요한가: 새 verifier가 추가될 때마다 같은 계약을 복사하면 문구 drift가 생긴다. 한 verifier는 `supporting_urls`, 다른 verifier는 evidence 표현을 다르게 해석하는 식의 불일치가 발생하기 쉽다.

구체 수정안:

- 공통 verifier 계약을 `skills/verifiers/CONTRACT.md`로 분리한다.
- 각 verifier skill에는 verifier-specific protocol만 남긴다.
- primary skill이 Task prompt에 공통 계약 요약을 포함해 subagent가 항상 같은 contract를 받게 한다.

### 2.3 `general-web` fallback은 비용 상한이 문서 단위로 없다

문제: `general-web`은 claim마다 WebSearch 1회 + WebFetch 최대 3회를 수행한다. fallback claim이 많은 문서에서는 verifier 호출 수와 외부 fetch 수가 급격히 증가한다.

왜 중요한가: 일반 사실 claim이 많은 브리핑에서는 비용과 시간이 커지고, 일부 환경에서는 WebFetch permission prompt도 늘어난다. 사용자는 “법률 인용 감사”를 기대했는데 일반 웹 검증이 대부분의 실행 시간을 차지할 수 있다.

구체 수정안:

- skill에 문서 단위 `general-web` 최대 claim 수 기본값을 둔다. 예: `max_general_web_claims = 10`.
- 초과 claim은 report에 `Skipped: general-web budget exceeded`로 표시한다.
- 사용자가 명시적으로 `--full-web`을 요청할 때만 제한을 해제한다.

### 2.4 DOCX source map이 block text를 중복 저장한다

문제: DOCX 추출 결과는 audit-source markdown 파일에 본문 전체를 쓰고, source map JSON의 각 block에도 동일 텍스트를 저장한다.

왜 중요한가: 대형 DOCX에서는 임시 파일 크기와 diff/로그 노출 면적이 커진다. 모델 토큰으로 직접 들어가지는 않더라도, 디버깅 중 source map을 읽으면 동일 본문이 중복 주입된다.

구체 수정안:

- `SourceBlock.text`는 기본적으로 생략하고 `--include-block-text` 디버그 옵션에서만 저장한다.
- report location lookup에는 `start/end/label/kind`만 사용한다.
- 테스트는 block text 대신 `markdown[start:end]` 정합으로 검증한다.

## 3. Architecture and Structure

### 3.1 Orchestration이 skill prompt에 과도하게 집중되어 있다

상태: 처리됨. `prepare` 명령으로 파일 타입 판정, temp work dir, aggregate 입출력 경로, DOCX sidecar output 경로 생성을 Python으로 내렸다. `finalize` 명령도 추가해 markdown render와 DOCX report 최종 분기를 prepare manifest 기반 Python 결정으로 옮겼다. Skill은 이제 `prepare -> chunk -> verifier dispatch -> aggregate -> finalize`만 수행한다.

문제: 파일 타입 판정, temp path 생성, chunk 실행, verifier dispatch, aggregate input 조립, render/report 분기까지 primary skill이 절차형 prompt로 들고 있다.

왜 중요한가: 절차가 길어질수록 모델이 한 단계를 빠뜨리거나 이전 단계 변수를 잘못 참조할 가능성이 커진다. v1.3에서 aggregate schema를 명시해야 했던 문제와 같은 유형의 회귀가 반복될 수 있다.

구체 수정안:

- Python에 `prepare` 명령을 추가한다.
  - 입력: 원본 path
  - 출력: `{ mode, source_path, audit_input, work_dir, paths }`
- Python에 `finalize` 명령을 추가한다.
  - 입력: prepare manifest + aggregated JSON
  - 출력: markdown render 또는 DOCX report
- skill은 `prepare -> chunk -> verifier dispatch -> aggregate -> finalize`만 수행하게 줄인다.

### 3.2 Markdown source와 DOCX source가 별도 개념으로 분기되어 있다

문제: markdown은 source map 없이 원문 offset을 직접 사용하고, DOCX는 source map을 사용한다. 두 경로가 계속 갈라지면 PDF/HTML 추가 시 다시 별도 분기가 생긴다.

왜 중요한가: 입력 포맷이 늘어날수록 chunk offset, report location, omission notice, output mode가 서로 다른 방식으로 구현되어 버그 표면이 넓어진다.

구체 수정안:

- 공통 `TextSource` 모델을 도입한다.
  - `source_type`
  - `source_path`
  - `audit_text_path`
  - `blocks`
  - `omissions`
- markdown 입력도 `TextSource`로 변환한다. 이때 block label은 `Line 1` 또는 `문단 N`으로 생성한다.
- `chunk`, `report`, `render`는 모두 `TextSource` 기반으로 동작하도록 통합한다.

### 3.3 DOCX ZIP 안전 검사는 있으나 OOXML 패키지 검증은 최소 수준이다

문제: v1.4.0은 zip entry 수, 압축비, path traversal을 검사하지만 `[Content_Types].xml`, `_rels/.rels`, `word/_rels/document.xml.rels` 같은 OOXML 구조 정합은 검증하지 않는다.

왜 중요한가: 깨진 DOCX나 비표준 zip이 `word/document.xml`만 갖고 있으면 통과할 수 있다. 이후 footnote/comment/hyperlink 지원이 붙으면 relationship 기반 외부 참조 처리에서 취약점이나 누락이 생기기 쉽다.

구체 수정안:

- `extract_docx` 시작 시 `[Content_Types].xml`과 `word/document.xml` 존재를 모두 확인한다.
- relationship 파일은 읽되 외부 target은 fetch하지 않고 `omissions`에 기록한다.
- OOXML package validation 실패 메시지를 CLI stderr에 명확히 출력한다.

### 3.4 감사 실행 manifest가 없다

문제: `.audit.md`에는 source path와 generated timestamp는 있지만, plugin version, input hash, local_only 여부, verifier 목록, max chunk tokens 같은 실행 조건이 없다.

왜 중요한가: 나중에 “왜 이 보고서에서 이 verdict가 나왔는지” 재현하려면 실행 조건이 필요하다. 법률 문서 감사에서는 재현성 자체가 품질 요소다.

구체 수정안:

- `AuditManifest` 모델을 추가한다.
- report header에 다음을 기록한다.
  - citation-auditor version
  - input SHA-256
  - audit-source SHA-256
  - verifier names + authority
  - local_only
  - max_chunk_tokens
- manifest JSON을 `.audit.json`으로 sidecar 저장하는 옵션을 추가한다.

## 4. Features

### 4.1 DOCX 각주/미주 추출 부재는 법률 use case에서 핵심 기능 공백이다

문제: v1.4.0은 본문과 표만 추출한다. 각주/미주에 있는 법령·판례·논문 인용은 감사 대상에서 빠진다.

왜 중요한가: 법률 의견서와 메모는 본문보다 각주에 출처가 집중되는 경우가 많다. 이 상태로는 “DOCX 감사 지원”이 실무 문서의 핵심 인용을 놓칠 수 있다.

구체 수정안:

- 다음 milestone에서 `word/footnotes.xml`, `word/endnotes.xml` 추출을 추가한다.
- source block label은 `각주 3`, `미주 2`로 표시한다.
- 본문 footnote reference 위치와 footnote block을 연결할 수 있으면 report detail에 “본문 문단 N에서 참조”를 추가한다.

### 4.2 `local_only` 사용법이 사용자 인터페이스에 노출되어 있지 않다

상태: 처리됨. slash command와 primary skill argument hint에 `--local-only`, `--no-web`, `--offline`을 추가했고, skill 1단계에서 `$ARGUMENTS`를 flags와 path로 분리하도록 명시했다.

문제: verifier 계약은 `local_only`를 지원하지만 slash command나 README에는 사용자가 어떤 문구/옵션으로 local-only 모드를 요청해야 하는지 정의되어 있지 않다.

왜 중요한가: 민감한 법률 문서를 다루는 사용자는 외부 fetch 차단을 명시적으로 원할 수 있다. UI가 없으면 skill이 “사용자가 명시적으로 요청한 경우”를 일관되게 판단하기 어렵다.

구체 수정안:

- slash command argument convention을 정의한다. 예: `/citation-auditor:audit --local-only path/to/file.docx`
- primary skill 1단계에서 `$ARGUMENTS`를 path와 flags로 분리하도록 지시한다.
- README Privacy 섹션에 local-only 예시와 한계를 추가한다.

### 4.3 DOCX report는 machine-readable output이 없다

상태: 처리됨. `report --out-json <path>`를 추가했고, markdown report는 동일 payload의 사람이 읽는 projection으로 렌더링한다.

문제: `.audit.md`는 사람이 읽기 좋지만, 다른 legal agent가 후속 수정 루프를 돌리기에는 파싱이 불안정하다.

왜 중요한가: 사용자는 여러 legal agent에 citation-auditor를 심어 쓰고 있다. 후속 agent가 `contradicted`/`unknown`만 읽어 수정 요청을 생성하려면 안정적인 JSON artifact가 필요하다.

구체 수정안:

- `report` CLI에 `--out-json <path>`를 추가한다.
- JSON에는 `findings: [{ id, label, location, claim, rationale, evidence }]`를 저장한다.
- markdown report는 이 JSON을 사람이 읽는 projection으로 취급한다.

### 4.4 실제 slash-command E2E fixture가 아직 없다

상태: 부분 처리됨. `fixtures/v1.4-docx-legal.docx`와 `fixtures/v1.4-docx-legal.expected.md`를 추가했고, Python component suite에서 DOCX fixture 추출 순서를 검증한다. Claude-run sidecar artifacts는 기대 label/location/summary와 일치한다. 다만 실제 slash-command 채팅 응답이 보고서 전문 대신 경로와 요약만 반환했는지는 transcript 확인이 필요하다.

문제: Python 테스트는 55개로 늘었고 DOCX sidecar artifact review도 통과했지만, v1.4.0 DOCX 경로의 실제 Claude Code slash-command transcript가 아직 repo에 기록되지 않았다.

왜 중요한가: 이 프로젝트의 위험 지점은 Python 유틸보다 skill orchestration이다. component test가 통과해도 skill이 temp path, aggregate schema, final report 경로를 잘못 처리할 수 있다.

구체 수정안:

- `fixtures/v1.4-docx-legal.docx`와 기대값 문서 `fixtures/v1.4-docx-legal.expected.md`를 추가한다.
- 실제 CC 세션에서 `/citation-auditor:audit fixtures/v1.4-docx-legal.docx`를 실행한다.
- CHANGELOG에 “component test”와 “real slash-command E2E”를 분리해 기록한다.

### 4.5 Vendor 업데이트 정책은 문서화되었지만 자동 보호장치가 없다

상태: 처리됨. `scripts/vendor-into.sh`에 `--confirm-docx-upgrade`를 추가했고, v1.3 vendored target에 v1.4+를 실제 적용할 때 플래그가 없으면 중단한다. `--dry-run`은 차단하지 않지만 DOCX 동작 활성화와 필요한 플래그를 출력한다.

문제: v1.4 계획 문서에는 각 legal agent를 전면 업데이트하지 말라고 되어 있지만, `scripts/vendor-into.sh` 자체에는 “v1.3 pin 유지”나 “canary 여부 확인” 같은 guard가 없다.

왜 중요한가: 한 번의 vendor 실행으로 skill과 Python 패키지가 모두 갱신된다. 실수로 여러 repo에 동시 적용하면 기존 안정 흐름을 흔들 수 있다.

구체 수정안:

- vendor script에 `--confirm-docx-upgrade` 플래그를 추가한다.
- v1.4 이상을 vendor할 때 target에 기존 `VENDOR.md`가 있고 버전이 v1.3이면 경고를 띄운다.
- `--dry-run` 출력에 “DOCX behavior will be enabled”를 명시한다.

## 5. Prompt Engineering Specifics

### 5.1 “citation-bearing” 표현이 모델의 추출 범위를 잘못 좁힌다

상태: 처리됨. 후속 마일스톤에서 “factual or citation-bearing” 의미가 되도록 primary skill 문구와 예시를 수정했다.

문제: skill 4단계의 “factual, citation-bearing claims”는 모델에게 “인용이 없는 사실 문장은 제외해도 된다”는 신호로 읽힐 수 있다.

왜 중요한가: 이 지시는 output quality 문제 1.1과 직접 연결된다. 추출 단계에서 놓친 claim은 verifier가 복구할 방법이 없다.

구체 수정안:

- 문구를 “factual claims and citation-bearing claims”로 바꾼다.
- “출처 없는 정량·날짜·법령명 주장은 감사 대상”이라는 positive example을 추가한다.
- speculation 제외 규칙은 유지하되 “구체 사실을 포함하면 추출” 예시를 넣는다.

### 5.2 DOCX 분기에서 temp path와 output path 생성 규칙이 모델 재량에 맡겨져 있다

상태: 처리됨. Python `prepare` 명령이 원본 파일을 받아 `mode`, `audit_input`, temp work dir, aggregate 입출력 경로, DOCX sidecar report 경로를 JSON으로 반환한다. DOCX sidecar `.audit.md` / `.audit.json`이 이미 있으면 기본은 실패하고, 사용자가 `--overwrite`를 명시한 경우에만 진행한다. Primary skill은 이제 `prepare` 결과의 `paths`만 사용한다.

문제: skill은 `<tmp-source.md>`, `<tmp-map.json>`, `<original-basename>.audit.md` 같은 placeholder를 제시하지만, 실제 안전한 temp path 생성 규칙은 없다.

왜 중요한가: 공백/한글/동명 파일이 있는 경로에서 모델이 잘못된 임시 파일명을 만들 수 있다. 같은 디렉토리에 기존 `.audit.md`가 있을 때 덮어쓰기 정책도 불명확하다.

구체 수정안:

- Python `prepare` 명령이 temp path와 output path를 결정하게 한다.
- output이 이미 있으면 기본은 fail, `--overwrite`가 있을 때만 덮어쓴다.
- skill에는 placeholder 대신 `python -m citation_auditor prepare "$0"` 한 줄만 남긴다.

### 5.3 Verifier JSON 실패 처리 정책이 너무 소극적이다

문제: primary skill은 verifier subagent가 invalid JSON을 반환하면 candidate를 drop하라고 한다. 재시도 규칙은 claim extraction에만 있고 verifier output에는 없다.

왜 중요한가: verifier 하나가 formatting 실수로 drop되면 최종 aggregate가 `none` 또는 낮은 authority verdict로 떨어질 수 있다. 사용자는 이를 source 불확실성으로 오해할 수 있다.

구체 수정안:

- verifier JSON parse 실패 시 1회 repair prompt를 수행한다.
- repair도 실패하면 report에 `Dropped verifier output: invalid JSON`을 audit metadata로 남긴다.
- `aggregate` 입력 생성 전 dropped candidates count를 Summary에 포함한다.

### 5.4 `local_only` 판단 기준이 자연어에 의존한다

상태: 처리됨. 명시 플래그(`--local-only`, `--no-web`, `--offline`)만 `local_only: true`로 인정하도록 primary skill을 갱신했다. 민감성 표현만 있고 플래그가 없으면 감사 시작 전에 확인하도록 했다.

문제: skill은 “unless the user explicitly requested local-only/private verification”이라고만 한다. 어떤 표현이 explicit request인지 명확하지 않다.

왜 중요한가: 사용자가 “민감한 문서야”라고 말했을 때 local_only로 볼지 애매하다. 반대로 단순히 “private repo”라는 말만 있어도 외부 fetch를 차단할 수 있다.

구체 수정안:

- 명시 flag만 인정한다. 예: `--local-only`, `--no-web`, `--offline`.
- flag가 없으면 기존 동작을 유지한다.
- 민감성 표현이 있으나 flag가 없으면 감사 시작 전 “외부 조회를 차단할까요?”라고 묻도록 한다.

### 5.5 Frontmatter custom fields가 장기적으로 schema drift 위험을 만든다

상태: 처리됨. bundled verifier의 `patterns`와 `authority`를 `metadata.patterns` / `metadata.authority`로 이동했고, primary skill은 legacy top-level field를 fallback으로 읽도록 갱신했다. Verifier authoring guide와 README 예시도 같은 구조로 맞췄다.

문제: verifier skill frontmatter는 `patterns`, `authority` 같은 custom field를 사용한다. 과거 CHANGELOG에도 frontmatter schema compliance 문제가 known limitation으로 남아 있다.

왜 중요한가: Claude Code plugin/skill 스키마가 엄격해지면 custom field가 경고에서 오류로 바뀔 수 있다. 그러면 verifier routing이 skill metadata에 의존하는 현재 구조가 깨진다.

구체 수정안:

- `patterns`와 `authority`를 `metadata:` 하위로 옮기는 migration을 진행한다.
- primary skill의 routing 규칙도 `metadata.patterns`, `metadata.authority`를 우선 읽고 legacy field를 fallback으로 읽게 한다.
- verifier authoring guide와 모든 bundled verifier를 같은 커밋에서 갱신한다.
