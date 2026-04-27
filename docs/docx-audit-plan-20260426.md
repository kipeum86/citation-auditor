# citation-auditor DOCX 지원 및 설계 감사 기획안

작성일: 2026-04-26

상태: draft, review 반영

## 1. 목표

`citation-auditor`를 markdown 전용 플러그인에서 DOCX 문서도 직접 감사할 수 있는 단독 검증 도구로 확장한다.

핵심 UX는 다음과 같다.

```text
input.docx
-> input.audit.md
```

원본 DOCX는 수정하지 않는다. 감사 결과는 별도 markdown 보고서로 생성한다. 이후 선택 기능으로 `input.audited.docx` 생성, 즉 DOCX 뒤에 감사표 appendix를 붙이는 기능을 추가할 수 있다.

동시에 현재 agent/project 구조에 대해 별도 엔지니어링 및 설계 감사 보고서를 작성한다. 이 감사는 칭찬이나 요약이 아니라 개선이 필요한 지점만 한국어로 정리한다.

## 2. UX 결정

### 기본값: 별도 `.audit.md` 보고서 생성

추천 기본 명령:

```bash
/citation-auditor:audit path/to/opinion.docx
```

생성물:

```text
path/to/opinion.audit.md
```

이 방식의 장점:

- 원본 DOCX가 변경되지 않아 법률 문서 워크플로우에서 심리적 부담이 작다.
- 보고서가 markdown이라 검색, diff, 버전관리, 에이전트 후속 처리에 유리하다.
- DOCX 서식 보존 문제를 MVP에서 피할 수 있다.
- 여러 legal agent가 동일한 감사 산출물을 읽고 재수정 루프를 만들기 쉽다.

### 옵션: DOCX 뒤에 감사표 appendix 첨부

후속 옵션:

```bash
/citation-auditor:audit path/to/opinion.docx --append-report
```

생성물:

```text
path/to/opinion.audit.md
path/to/opinion.audited.docx
```

이 기능은 Word 안에서만 검토하려는 사용자에게 좋지만, MVP 기본값으로 두기에는 문서 변형 리스크가 있다. 따라서 v1에서는 `.audit.md`를 canonical output으로 삼고, DOCX appendix는 v1.x 후속 기능으로 분리한다.

## 3. 범위

### MVP에 포함

- `.docx` 입력 감지
- DOCX 본문 텍스트 추출
- 표 안의 텍스트 추출
- paragraph/table 순서 보존
- 추출된 내용을 audit용 markdown으로 변환
- source map JSON 생성
- 기존 chunk -> claim extraction -> verifier -> aggregate 흐름 재사용
- 최종 결과를 `.audit.md` 보고서로 저장
- slash command와 skill 지시문에서 `.md` / `.docx` 분기 명확화
- 테스트 문서 생성 기반의 DOCX 추출 테스트

### MVP에서 제외

- 원본 DOCX 본문에 inline badge 삽입
- Word comment 삽입
- tracked changes 생성
- 각주/미주 완전 지원
- 페이지 번호 정확 계산
- 이미지/OCR
- 복잡한 numbering style 재현
- DOCX appendix 생성

이 제외 항목은 불필요해서가 아니라, MVP에서 넣으면 OOXML 편집 복잡도가 급격히 올라가고 원본 문서 손상 리스크가 커지기 때문이다.

## 4. 제안 아키텍처

현재 markdown 구조:

```text
markdown file
-> chunk
-> claim extraction by skill
-> verifier subagents
-> aggregate
-> render annotated markdown
```

DOCX 지원 후 구조:

```text
input file
-> prepare deterministic audit paths
-> if .docx: extract-docx
-> audit-source markdown text
-> chunk
-> claim extraction by skill
-> verifier subagents
-> aggregate
-> finalize from prepare manifest
-> if original input was .md: annotated markdown stdout
-> if original input was .docx: external audit report markdown/json sidecars
```

중요한 점은 DOCX를 직접 verifier에 넣지 않는 것이다. 기존 offset 기반 파이프라인은 markdown/text 기준으로 설계되어 있으므로, DOCX는 먼저 감사용 중간 markdown으로 변환한다.

## 5. 새 Python 모듈 설계

### `citation_auditor/docx.py`

역할:

- `.docx` zip 내부의 `word/document.xml` 읽기
- OOXML paragraph/table 텍스트를 문서 순서대로 추출
- 감사용 markdown 문자열 생성
- 원본 위치 메타데이터 생성
- ZIP 엔트리 안전성 검사

권장 구현 방식:

- `zipfile`
- `xml.etree.ElementTree`
- `python-docx`는 선택적으로만 고려

`python-docx`는 단순 paragraph/table 추출에는 편하지만, 장기적으로 footnote/comment/OOXML anchor를 다루려면 zip+xml 기반이 더 투명하다. 런타임 의존성 최소 원칙을 유지하려면 표준 라이브러리 XML부터 시작하는 편이 좋다.

텍스트 추출 정책:

- 본문 텍스트는 `<w:body>`의 paragraph/table 안에 있는 `<w:t>` 텍스트를 기준으로 한다.
- `<w:hyperlink>` 안의 텍스트는 본문 흐름에 포함하되, hyperlink 대상 URL은 MVP에서 별도 evidence/source 메타로 보관하지 않는다.
- `numbering.xml` 기반 번호 재구성은 하지 않는다. 단, list 문단을 판별할 수 있으면 `kind: list_item`으로 표시한다.
- `<w:del>` 삭제 텍스트는 MVP 감사 대상에서 제외한다.
- `<w:ins>` 삽입 텍스트는 현재 보이는 본문으로 취급해 포함한다.
- `<w:commentReference>`와 `comments.xml`의 코멘트 본문은 MVP 감사 대상에서 제외한다.
- 각주/미주(`footnotes.xml`, `endnotes.xml`)는 MVP에서 제외하고 후속 milestone으로 분리한다.

예상 source map 모델:

```json
{
  "source_type": "docx",
  "source_path": "opinion.docx",
  "markdown_path": "/tmp/opinion.audit-source.md",
  "blocks": [
    {
      "id": "P0001",
      "kind": "paragraph",
      "label": "문단 1",
      "text": "...",
      "start": 0,
      "end": 42
    },
    {
      "id": "T001R02C03",
      "kind": "table_cell",
      "label": "표 1 / 행 2 / 열 3",
      "text": "...",
      "start": 80,
      "end": 120
    }
  ]
}
```

Block offset 규약:

- `start`, `end`는 audit-source markdown의 character offset이다. 0-based half-open interval(`[start, end)`)로 기록한다.
- block 사이 separator(`\n\n`)는 audit-source markdown offset에는 포함되지만 어느 block에도 속하지 않는다.
- `report`는 `AggregateOutput`의 `claim.sentence_span.start`가 속하는 block을 location으로 채택한다.
- claim span이 두 block 이상에 걸치면 시작 block 라벨에 `(이어짐)`을 붙인다.
- 특정 offset이 어느 block에도 속하지 않으면 `Location: 위치 미상`으로 표기한다.
- 같은 block에 여러 claim이 잡히면 `C-001`, `C-002` 같은 finding ID로만 구분하고, location label은 동일하게 유지한다.

### `citation_auditor/report.py`

역할:

- `AggregateOutput`을 사람이 읽기 좋은 별도 감사 보고서로 렌더
- 원문 전체에 badge를 삽입하지 않음
- 요약표, finding 목록, evidence 목록 생성
- DOCX source block label을 location으로 표시

출력 예:

```markdown
# Citation Audit Report

- Source: opinion.docx
- Generated: 2026-04-26
- Mode: external report

## Summary

| Verdict | Count |
|---|---:|
| contradicted | 2 |
| unknown | 3 |
| verified | 8 |

## Findings

| ID | Verdict | Location | Verifier | Claim |
|---|---|---|---|---|
| C-001 | contradicted | 문단 12 | korean-law | ... |

## Details

### C-001

- Verdict: contradicted
- Location: 문단 12
- Claim: ...
- Rationale: ...
- Evidence: ...
```

## 6. CLI 변경안

현재 CLI:

```bash
python -m citation_auditor chunk input.md
python -m citation_auditor aggregate agg-input.json
python -m citation_auditor render input.md aggregated.json
python -m citation_auditor korean_law parse "민법 제103조"
python -m citation_auditor korean_law extract-hang article.txt 2
python -m citation_auditor korean_law extract-ho hang.txt 2
python -m citation_auditor korean_law normalize-case "대법원-2023-다-302036"
python -m citation_auditor korean_law lookup-law "민법"
```

추가할 CLI 시그니처는 다음으로 고정한다.

```bash
python -m citation_auditor prepare input.docx
python -m citation_auditor prepare input.docx --overwrite
python -m citation_auditor extract-docx input.docx --out-md <paths.audit_source_md> --out-map <paths.source_map_json>
python -m citation_auditor finalize <paths.prepare_manifest_json> <paths.aggregate_output_json>
python -m citation_auditor report <paths.source_map_json> <paths.aggregate_output_json> --out <paths.report_md> --out-json <paths.report_json>
```

규약:

- `prepare`는 원본 path를 받아 mode, audit input path, work dir, aggregate 입출력 path, DOCX sidecar output path를 짧은 JSON으로 출력한다.
- `prepare` stdout은 skill이 `paths.prepare_manifest_json`에 그대로 저장한다.
- `.docx` 입력에서 기존 `.audit.md` 또는 `.audit.json`이 있으면 기본은 non-zero exit이고, 사용자가 `--overwrite`를 명시한 경우에만 진행한다.
- skill은 temp path나 sidecar output path를 직접 만들지 않고 항상 `prepare` JSON의 `paths` 값을 사용한다.
- `extract-docx`는 audit-source markdown과 source map JSON을 명시 경로에 쓴다.
- `extract-docx`의 stdout은 사람이 읽는 로그가 아니라 다음 형태의 짧은 JSON만 출력한다.

```json
{ "markdown": "/tmp/input.audit-source.md", "map": "/tmp/input.map.json" }
```

- `report`의 첫 번째 인자는 항상 source map JSON이다.
- `report`의 두 번째 인자는 항상 `aggregate`가 출력한 `AggregateOutput` JSON이다.
- `report --out`이 없으면 stdout으로 보고서를 출력한다. skill에서는 항상 `--out`을 사용한다.
- `finalize`는 prepare manifest의 mode에 따라 markdown 입력은 annotated markdown을 stdout으로 출력하고, DOCX 입력은 `report`를 호출해 `.audit.md`/`.audit.json`을 생성한 뒤 짧은 JSON summary만 stdout으로 출력한다.

MVP에서 skill이 수행할 전체 DOCX 흐름:

```bash
python -m citation_auditor prepare input.docx
python -m citation_auditor extract-docx input.docx --out-md <paths.audit_source_md> --out-map <paths.source_map_json>
python -m citation_auditor chunk <audit_input> --max-tokens 3000
# claim extraction -> verifier dispatch는 skill이 수행
python -m citation_auditor aggregate <paths.aggregate_input_json> > <paths.aggregate_output_json>
python -m citation_auditor finalize <paths.prepare_manifest_json> <paths.aggregate_output_json>
```

## 7. Skill 변경안

`skills/citation-auditor/SKILL.md`의 1단계를 다음처럼 바꾼다.

현재:

```text
Confirm $0 exists and is a markdown file.
```

변경:

```text
Confirm $0 exists and has extension .md, .markdown, or .docx.

1. Determine the input extension.
2. Run prepare to obtain deterministic paths. Pass --overwrite only when the user explicitly supplied it.
   - Write the prepare stdout to paths.prepare_manifest_json.
3. If the input is .md or .markdown, run the existing markdown pipeline with the prepare-provided audit_input.
4. If the input is .docx:
   - Run extract-docx with the prepare-provided audit_source_md and source_map_json paths.
   - Treat the temporary audit-source markdown as the document input for all existing claim extraction, verifier routing, Task dispatch, invalid JSON handling, skipped forecast handling, and aggregate schema rules.
   - Preserve the existing aggregate input schema exactly.
   - Replace the final render/report branch with finalize <paths.prepare_manifest_json> <paths.aggregate_output_json>.
   - Return only the generated report path plus a concise Summary table. Do not paste the full report into chat.
```

중요한 출력 정책:

- `.md` 입력: 기존처럼 annotated markdown 반환
- `.docx` 입력: 원본 수정 없이 `.audit.md` 파일 생성
- DOCX 감사 결과를 채팅에 전문 출력하지 않음
- 보고서 파일 경로와 요약만 반환

`local_only` 전파 정책:

- DOCX 분기에서도 verifier subagent에 전달되는 입력 JSON은 markdown 분기와 동일한 규약을 따른다.
- `--local-only`, `--no-web`, `--offline` 중 하나가 명시된 경우에만 `local_only` 값은 audit-source markdown에서 추출된 claim에도 그대로 전파한다.
- 민감/비밀/특권 문서라는 자연어 표현만 있고 명시 flag가 없으면, skill은 감사를 시작하기 전에 외부 조회 차단 여부를 확인한다.
- DOCX 추출 자체는 로컬 deterministic 처리이므로 외부 네트워크를 사용하지 않는다.

## 8. Slash Command 변경안

`commands/audit.md`

현재 설명:

```text
Audit a markdown file
argument-hint: "<file.md>"
```

변경:

```text
Audit a markdown or DOCX file
argument-hint: "[--local-only|--no-web|--offline] [--overwrite] <file.md|file.docx>"
```

본문도 함께 수정한다.

- 무인자일 때 질문: “markdown or DOCX file path” 요청
- path 전달 문구: “markdown file path”가 아니라 “file path” 또는 “markdown/DOCX file path”로 수정
- `--overwrite`는 기존 DOCX sidecar report를 의도적으로 교체할 때만 전달한다고 명시
- `.docx` 입력은 최종 annotated markdown 전문을 반환하지 않고 `.audit.md` 파일 경로를 반환한다고 명시

## 9. 테스트 계획

### 단위 테스트

- `test_extract_docx_paragraphs`: 간단한 DOCX에서 paragraph 2개 추출
- `test_extract_docx_tables`: 표 셀 텍스트가 순서대로 추출되는지 확인
- `test_extract_docx_ignores_empty_paragraphs`: 빈 문단이 과도한 공백을 만들지 않는지 확인
- `test_report_renders_summary_counts`: verdict별 count가 맞는지 확인
- `test_report_includes_location_from_source_map`: 문단/표 위치가 finding에 표시되는지 확인
- `test_chunk_offsets_align_with_docx_blocks`: `extract-docx` -> `chunk` 후 chunk segment의 `document_start/end`가 source map block offset과 정합되는지 확인
- `test_report_location_is_block_label`: aggregate 결과를 report에 넣었을 때 `Location`이 source map의 `block.label`과 일치하는지 확인
- `test_prepare_subcommand_returns_markdown_paths`: markdown 입력에서 prepare가 원문을 audit_input으로 유지하는지 확인
- `test_prepare_subcommand_returns_docx_paths_for_spaced_unicode_input`: 공백/한글이 있는 DOCX 경로에서 prepare가 안전한 temp path와 sidecar path를 반환하는지 확인
- `test_prepare_subcommand_blocks_existing_docx_outputs_without_overwrite`: 기존 sidecar가 있을 때 기본 차단, `--overwrite` 허용을 확인
- `test_finalize_subcommand_renders_markdown_from_prepare_manifest`: markdown manifest + aggregate output으로 annotated markdown이 생성되는지 확인
- `test_finalize_subcommand_writes_docx_sidecar_reports`: DOCX manifest + aggregate output으로 `.audit.md`/`.audit.json`과 짧은 summary JSON이 생성되는지 확인
- `test_finalize_subcommand_blocks_stale_docx_manifest_without_overwrite`: 오래된 prepare manifest로 기존 sidecar를 덮어쓰지 않는지 확인

### CLI 테스트

- `prepare`가 지원 확장자만 허용하고 mode별 path manifest를 JSON으로 출력하는지 확인
- `finalize`가 prepare manifest의 mode별로 markdown stdout 또는 DOCX sidecar report를 생성하는지 확인
- `extract-docx`가 markdown과 map JSON을 생성하는지 확인
- `report`가 `.audit.md`를 생성하는지 확인
- 잘못된 확장자 또는 깨진 docx에서 non-zero exit
- `extract-docx` stdout이 `{ "markdown": "...", "map": "..." }` JSON만 출력하는지 확인
- `report`가 offset이 어느 block에도 속하지 않는 claim을 `위치 미상`으로 표시하는지 확인

### E2E 검증

component test와 simulation은 E2E로 부르지 않는다. 실제 Claude Code 터미널에서 slash command를 실행해 검증한다.

필수 fixture:

- 짧은 Korean legal DOCX fixture
- 표 안에 법령 인용이 있는 DOCX fixture
- 영어/한국어 혼합 DOCX fixture

통과 기준:

- `/citation-auditor:audit fixtures/<sample>.docx`가 실제 CC 세션에서 `.docx` 분기로 들어가는 것을 trace로 확인한다.
- 사람이 의도적으로 심은 hallucination이 `contradicted`로 잡히는지 확인한다. 기준은 v1.2 global legal fixture처럼 claim 단위 기대값을 사전에 적어 두고 비교한다.
- 결과 `.audit.md`가 생성된다.
- 채팅에는 보고서 전문이 출력되지 않고, 보고서 경로와 요약만 반환된다.
- 기존 `/citation-auditor:audit fixtures/<sample>.md` markdown 경로가 v1.3과 동일하게 동작한다.

## 10. 의존성 정책

가능하면 새 런타임 의존성을 추가하지 않는다.

1차 후보:

- 표준 라이브러리 `zipfile`
- 표준 라이브러리 `xml.etree.ElementTree`

추가 의존성이 필요할 때만:

- `lxml`: OOXML namespace 처리와 XPath가 편하지만 의존성 증가
- `python-docx`: 생성/간단 읽기는 편하지만 footnote/comment 처리 한계 있음

MVP는 표준 라이브러리 기반으로 시작하는 것이 현재 프로젝트의 “deterministic utility, minimal deps” 원칙과 맞다.

## 11. 위험과 대응

### 위험: 비정상 DOCX 입력

대응:

- DOCX를 디스크에 풀지 않고 `zipfile.ZipFile.read("word/document.xml")` 방식으로 필요한 XML만 읽는다.
- ZIP 엔트리 이름을 `os.path.normpath`로 정규화해 절대경로 또는 `..` 포함 엔트리를 거절한다.
- `ZipInfo.file_size` 합계와 `compress_size` 합계의 압축비가 임계값(예: 100배)을 넘으면 거절한다.
- ZIP 항목 수와 전체 uncompressed size에 상한을 둔다.

### 위험: track changes / comments / hyperlinks / numbering 처리 혼선

대응:

- MVP 텍스트 추출 정책을 `docx.py` 섹션의 규약으로 고정한다.
- 삭제 텍스트(`<w:del>`)와 코멘트 본문은 감사 대상에서 제외한다.
- 삽입 텍스트(`<w:ins>`)와 hyperlink 표시 텍스트는 현재 보이는 본문으로 취급한다.
- numbering 재구성은 하지 않는다. list item 여부만 metadata에 남긴다.

### 위험: DOCX 원문 위치와 추출 markdown offset 불일치

대응:

- 원본 DOCX에 직접 badge를 넣지 않는다.
- 보고서 location은 “문단 N / 표 N 행 N 열 N” 수준으로 둔다.
- 정확한 Word 위치 복원은 후속 기능으로 분리한다.

### 위험: 각주/미주에 핵심 인용이 있는데 MVP가 누락

대응:

- MVP 문서에 명시한다.
- 후속 milestone으로 `footnotes.xml`, `endnotes.xml` 추출을 추가한다.

### 위험: 보고서가 너무 길어짐

대응:

- Summary -> Findings table -> Details 순서로 구성한다.
- `contradicted` / `unknown`을 상단에 우선 배치한다.
- `verified` 항목은 기본적으로 하단에 배치하거나 설정으로 생략할 수 있게 한다.

### 위험: skill 지시문이 너무 길어져 token 비용 증가

대응:

- DOCX 분기만 skill에 추가한다.
- 세부 보고서 formatting은 Python `report.py`에 맡긴다.
- prompt에는 schema와 필수 절차만 남긴다.

## 12. 버전 전략

이 변경은 사용자에게 보이는 기능 추가이므로 minor version이 적절하다.

추천:

```text
v1.4.0
```

릴리스 노트 핵심:

- DOCX input support
- External `.audit.md` report generation
- Original DOCX remains untouched
- Markdown audit flow unchanged

운영 규칙:

- `.claude-plugin/plugin.json`과 `pyproject.toml`의 `version`을 모두 `1.4.0`으로 올린다.
- Claude Code 플러그인 캐시 드리프트를 피하기 위해 동일 버전 문자열로 재배포하지 않는다.
- 사용자 안내에는 `/plugin update citation-auditor@citation-auditor` 또는 재설치 절차를 포함한다.
- vendored 사용자는 자동 업데이트되지 않으므로 별도 vendor 전략을 따른다.

## 13. 리걸 에이전트 vendored copy 업데이트 판단

본체 `citation-auditor`에는 DOCX 기능을 추가하는 것이 맞다. 단, 각 legal agent repo에 심어둔 vendored copy는 즉시 전면 업데이트하지 않는다.

판단:

- 기존 markdown 감사가 잘 작동 중이면 vendored copy는 그대로 둔다.
- DOCX 직접 감사가 필요한 repo 1개만 canary로 업데이트한다.
- canary에서 며칠 사용해 보고 문제가 없으면, 나머지는 필요할 때만 순차 업데이트한다.
- 모든 리포에 같은 날 동시에 vendor 업데이트를 push하지 않는다.

이유:

- vendored copy는 각 agent의 안정적인 pinned dependency 역할을 한다.
- skill prompt 변경은 코드 변경보다 회귀 예측이 어렵다.
- 현재 cross-repo 정리 문맥에서는 동시 remediation/update wave 자체가 불필요한 시그널이 될 수 있다.
- global plugin을 업데이트해도 프로젝트 로컬 `.claude/skills/citation-auditor`가 우선되면 각 agent는 기존 버전으로 계속 동작할 가능성이 높다. 이는 단점이 아니라 안정성 장치로 취급한다.

업데이트 기준:

| 상황 | 각 에이전트 업데이트 필요 여부 |
|---|---|
| `.md`만 감사함 | 불필요 |
| DOCX를 에이전트 안에서 직접 감사해야 함 | 필요 |
| 기존 감사 품질에 불만 없음 | 보류 |
| 새 버전에 markdown 감사 버그픽스가 포함됨 | 해당 에이전트만 선별 업데이트 |
| vendored copy 없이 global plugin만 사용함 | 본체 업데이트만으로 충분 |

`scripts/vendor-into.sh` 정합:

- vendor 스크립트는 `citation_auditor/` 패키지 전체를 복사하므로, v1.4.0을 vendor하면 `docx.py`와 `report.py`도 자동으로 들어간다.
- 다만 실제 DOCX UX는 `.claude/skills/citation-auditor/SKILL.md`의 `.docx` 분기가 있어야 활성화된다.
- v1.3 vendored copy 위에 v1.4 이상을 실제 적용할 때는 `scripts/vendor-into.sh --confirm-docx-upgrade`가 필요하다. 플래그가 없으면 스크립트가 중단되어 bulk update를 막는다.
- `--dry-run`은 중단하지 않지만, DOCX 동작이 활성화될 것과 실제 적용에 필요한 확인 플래그를 출력한다.
- DOCX를 의도하지 않는 agent는 v1.3.x tag 또는 commit으로 checkout한 뒤 vendor를 실행해 pin 상태를 유지한다.
- agent별로 skill을 local customization 한 경우, vendor 스크립트가 `.claude/skills/citation-auditor/`를 덮어쓴다는 점을 작업 전 확인한다.

## 14. 동시에 수행할 엔지니어링/설계 감사 계획

사용자가 제공한 감사 프롬프트는 별도 산출물로 실행한다. 다만 reviewer attention 분산을 줄이기 위해 DOCX 기획안을 먼저 닫고, 그다음 별도 문서로 진행한다.

추천 파일명:

```text
docs/audit-20260426-engineering-design.md
```

감사 범위:

1. Output Quality
2. Token Efficiency
3. Architecture and Structure
4. Features
5. Prompt Engineering Specifics

작성 원칙:

- 한국어로 작성
- 잘 된 점은 쓰지 않음
- 각 finding마다 다음 3개 포함
  - 문제
  - 왜 중요한지
  - 구체적 수정안
- 추상적 제안 금지
- 코드 요약 금지

현재 이미 보이는 후보 finding:

- markdown offset 기반 렌더링이 DOCX/비문자 소스 확장에 취약함
- primary skill이 지나치게 긴 절차형 prompt가 되어 token 비용과 실행 오류 가능성이 커짐
- claim extraction schema는 있지만 실제 강제는 Claude structured output 의존이라 실패 시 관측성이 약함
- verifier skill마다 “JSON만 반환” 같은 반복 지시가 많아 공통 계약 문서/짧은 shared protocol로 줄일 여지가 있음
- verified 항목까지 모두 inline badge와 report에 노출하면 긴 문서에서 reviewer attention이 분산됨
- slash command와 README가 markdown 중심이라 단독 플러그인 UX를 제한함
- DOCX, PDF 등 실무 입력 포맷 부재가 legal use case에서 핵심 병목임

## 15. 구현 순서 제안

1. `docx.py`로 DOCX -> audit-source markdown 추출
2. `report.py`로 external audit report 생성
3. CLI에 `extract-docx`, `report` 추가
4. CLI에 `prepare` 추가해서 temp path와 sidecar output path를 Python이 결정하게 함
5. CLI에 `finalize` 추가해서 markdown render와 DOCX report 분기를 Python이 결정하게 함
6. skill에서 `.docx` 분기 추가
7. slash command 문구 수정
8. README/KO README에 DOCX 사용법 추가
9. 테스트 추가
10. changelog/version bump
11. 실제 CC 세션에서 DOCX E2E 검증
12. 필요할 경우 canary legal agent 1개만 vendor 업데이트
13. 별도 엔지니어링/설계 감사 문서 작성

이 순서가 좋은 이유는, 기존 markdown 파이프라인을 먼저 건드리지 않고 DOCX 변환과 보고서 생성을 옆에 붙일 수 있기 때문이다. 실패해도 기존 `/audit file.md` 동작을 망가뜨릴 가능성이 작다.
