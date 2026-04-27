import json
import subprocess
import sys
import zipfile
from pathlib import Path

from citation_auditor.korean_law import CitationRef
from citation_auditor.models import AggregateOutput, ChunkOutput


def _run_module(repo_root: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "citation_auditor", *args],
        cwd=repo_root,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_chunk_subcommand_prints_valid_json(repo_root: Path, tmp_path: Path) -> None:
    source = tmp_path / "input.md"
    source.write_text("One.\n\nTwo.\n\nThree.", encoding="utf-8")

    result = _run_module(repo_root, "chunk", str(source), "--max-tokens", "5")

    assert result.returncode == 0
    payload = ChunkOutput.model_validate_json(result.stdout)
    assert len(payload.chunks) >= 2


def test_aggregate_subcommand_accepts_file_and_normalizes_offsets(repo_root: Path, tmp_path: Path) -> None:
    verdicts_path = tmp_path / "verdicts.json"
    verdicts_path.write_text(
        json.dumps(
            {
                "verdicts": [
                    {
                        "chunk": {
                            "index": 0,
                            "text": "Alpha claim.",
                            "segments": [
                                {
                                    "chunk_start": 0,
                                    "chunk_end": 12,
                                    "document_start": 100,
                                    "document_end": 112,
                                }
                            ],
                        },
                        "claim": {
                            "text": "Alpha claim.",
                            "sentence_span": {"start": 0, "end": 12},
                            "claim_type": "factual",
                            "suggested_verifier": "general-web",
                            "audit_reason": "factual",
                        },
                        "candidates": [
                            {
                                "claim": {
                                    "text": "Alpha claim.",
                                    "sentence_span": {"start": 0, "end": 12},
                                    "claim_type": "factual",
                                    "suggested_verifier": "general-web",
                                    "audit_reason": "factual",
                                },
                                "label": "verified",
                                "verifier_name": "general-web",
                                "authority": 0.5,
                                "rationale": "Looks right.",
                                "evidence": [{"url": "https://example.com"}],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = _run_module(repo_root, "aggregate", str(verdicts_path))

    assert result.returncode == 0
    payload = AggregateOutput.model_validate_json(result.stdout)
    assert payload.aggregated[0].claim.sentence_span.start == 100
    assert payload.aggregated[0].verdict.claim.sentence_span.end == 112
    assert payload.aggregated[0].claim.audit_reason == "factual"


def test_aggregate_subcommand_accepts_stdin_via_dash(repo_root: Path) -> None:
    raw_input = json.dumps(
        {
            "verdicts": [
                {
                    "chunk": {
                        "index": 1,
                        "text": "Beta claim.",
                        "segments": [
                            {
                                "chunk_start": 0,
                                "chunk_end": 11,
                                "document_start": 50,
                                "document_end": 61,
                            }
                        ],
                    },
                    "claim": {
                        "text": "Beta claim.",
                        "sentence_span": {"start": 0, "end": 11},
                        "claim_type": "factual",
                        "suggested_verifier": "general-web",
                    },
                    "candidates": [],
                }
            ]
        }
    )

    result = _run_module(repo_root, "aggregate", "-", input_text=raw_input)

    assert result.returncode == 0
    payload = AggregateOutput.model_validate_json(result.stdout)
    assert payload.aggregated[0].verdict.verifier_name == "none"


def test_render_subcommand_prints_annotated_markdown(repo_root: Path, tmp_path: Path) -> None:
    markdown_path = tmp_path / "input.md"
    aggregate_path = tmp_path / "aggregated.json"
    markdown_path.write_text("Normal sentence one.", encoding="utf-8")
    aggregate_path.write_text(
        json.dumps(
            {
                "aggregated": [
                    {
                        "claim": {
                            "text": "Normal sentence one.",
                            "sentence_span": {"start": 0, "end": 20},
                            "claim_type": "factual",
                            "suggested_verifier": "general-web",
                        },
                        "verdict": {
                            "claim": {
                                "text": "Normal sentence one.",
                                "sentence_span": {"start": 0, "end": 20},
                                "claim_type": "factual",
                                "suggested_verifier": "general-web",
                            },
                            "label": "verified",
                            "verifier_name": "general-web",
                            "authority": 0.5,
                            "rationale": "Checked.",
                            "evidence": [],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = _run_module(repo_root, "render", str(markdown_path), str(aggregate_path))

    assert result.returncode == 0
    assert "Normal sentence one. **[✅ general-web]**" in result.stdout


def test_prepare_subcommand_returns_markdown_paths(repo_root: Path, tmp_path: Path) -> None:
    markdown_path = tmp_path / "input.md"
    markdown_path.write_text("Normal sentence one.", encoding="utf-8")

    result = _run_module(repo_root, "prepare", str(markdown_path))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "markdown"
    assert payload["source_type"] == "markdown"
    assert payload["source_path"] == str(markdown_path.resolve())
    assert payload["audit_input"] == str(markdown_path.resolve())
    assert Path(payload["work_dir"]).is_dir()
    assert payload["paths"]["audit_source_md"] is None
    assert payload["paths"]["source_map_json"] is None
    assert payload["paths"]["report_md"] is None
    assert payload["paths"]["report_json"] is None
    assert Path(payload["paths"]["aggregate_input_json"]).parent == Path(payload["work_dir"])
    assert Path(payload["paths"]["aggregate_output_json"]).parent == Path(payload["work_dir"])


def test_prepare_subcommand_returns_docx_paths_for_spaced_unicode_input(repo_root: Path, tmp_path: Path) -> None:
    docx_path = tmp_path / "의견서 초안.docx"
    _write_docx(docx_path, "<w:p><w:r><w:t>민법 제103조 인용.</w:t></w:r></w:p>")

    result = _run_module(repo_root, "prepare", str(docx_path))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "docx_report"
    assert payload["source_type"] == "docx"
    assert payload["source_path"] == str(docx_path.resolve())
    assert Path(payload["work_dir"]).is_dir()
    assert Path(payload["audit_input"]).parent == Path(payload["work_dir"])
    assert payload["paths"]["audit_source_md"] == payload["audit_input"]
    assert Path(payload["paths"]["source_map_json"]).parent == Path(payload["work_dir"])
    assert payload["paths"]["report_md"] == str((tmp_path / "의견서 초안.audit.md").resolve())
    assert payload["paths"]["report_json"] == str((tmp_path / "의견서 초안.audit.json").resolve())


def test_prepare_subcommand_blocks_existing_docx_outputs_without_overwrite(repo_root: Path, tmp_path: Path) -> None:
    docx_path = tmp_path / "input.docx"
    _write_docx(docx_path, "<w:p><w:r><w:t>민법 제103조 인용.</w:t></w:r></w:p>")
    (tmp_path / "input.audit.md").write_text("old report", encoding="utf-8")

    blocked = _run_module(repo_root, "prepare", str(docx_path))
    allowed = _run_module(repo_root, "prepare", str(docx_path), "--overwrite")

    assert blocked.returncode != 0
    assert "already exists" in blocked.stderr
    assert "--overwrite" in blocked.stderr
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["overwrite"] is True


def test_extract_docx_subcommand_writes_markdown_and_map(repo_root: Path, tmp_path: Path) -> None:
    docx_path = tmp_path / "input.docx"
    markdown_path = tmp_path / "input.audit-source.md"
    map_path = tmp_path / "input.map.json"
    _write_docx(docx_path, "<w:p><w:r><w:t>민법 제103조 인용.</w:t></w:r></w:p>")

    result = _run_module(
        repo_root,
        "extract-docx",
        str(docx_path),
        "--out-md",
        str(markdown_path),
        "--out-map",
        str(map_path),
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"markdown": str(markdown_path), "map": str(map_path)}
    assert markdown_path.read_text(encoding="utf-8") == "민법 제103조 인용."
    payload = json.loads(map_path.read_text(encoding="utf-8"))
    assert payload["blocks"][0]["label"] == "문단 1"


def test_extract_docx_invalid_input_fails_nonzero(repo_root: Path, tmp_path: Path) -> None:
    invalid_docx = tmp_path / "invalid.docx"
    invalid_docx.write_text("not a zip", encoding="utf-8")

    result = _run_module(
        repo_root,
        "extract-docx",
        str(invalid_docx),
        "--out-md",
        str(tmp_path / "out.md"),
        "--out-map",
        str(tmp_path / "out.json"),
    )

    assert result.returncode != 0
    assert "valid DOCX" in result.stderr


def test_report_subcommand_writes_external_markdown(repo_root: Path, tmp_path: Path) -> None:
    map_path = tmp_path / "input.map.json"
    aggregate_path = tmp_path / "aggregated.json"
    report_path = tmp_path / "input.audit.md"
    report_json_path = tmp_path / "input.audit.json"
    map_path.write_text(
        json.dumps(
            {
                "source_type": "docx",
                "source_path": "input.docx",
                "blocks": [
                    {
                        "id": "P0001",
                        "kind": "paragraph",
                        "label": "문단 1",
                        "text": "Normal sentence one.",
                        "start": 0,
                        "end": 20,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    aggregate_path.write_text(
        json.dumps(
            {
                "aggregated": [
                    {
                        "claim": {
                            "text": "Normal sentence one.",
                            "sentence_span": {"start": 0, "end": 20},
                            "claim_type": "factual",
                            "suggested_verifier": "general-web",
                        },
                        "verdict": {
                            "claim": {
                                "text": "Normal sentence one.",
                                "sentence_span": {"start": 0, "end": 20},
                                "claim_type": "factual",
                                "suggested_verifier": "general-web",
                            },
                            "label": "unknown",
                            "verifier_name": "general-web",
                            "authority": 0.5,
                            "rationale": "Not enough evidence.",
                            "evidence": [],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = _run_module(
        repo_root,
        "report",
        str(map_path),
        str(aggregate_path),
        "--out",
        str(report_path),
        "--out-json",
        str(report_json_path),
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"report": str(report_path), "json": str(report_json_path)}
    report = report_path.read_text(encoding="utf-8")
    assert "| unknown | 1 |" in report
    assert "| C-001 | unknown | 문단 1 | general-web | Normal sentence one. |" in report
    payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert payload["summary"] == {"contradicted": 0, "unknown": 1, "verified": 0, "total": 1}
    assert payload["findings"][0]["id"] == "C-001"
    assert payload["findings"][0]["location"] == "문단 1"
    assert payload["findings"][0]["claim"] == "Normal sentence one."


def test_aggregate_invalid_json_fails_nonzero(repo_root: Path, tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not valid json", encoding="utf-8")

    result = _run_module(repo_root, "aggregate", str(invalid_path))

    assert result.returncode != 0
    assert result.stderr.strip()


def test_korean_law_parse_subcommand_prints_valid_json(repo_root: Path) -> None:
    result = _run_module(repo_root, "korean_law", "parse", "민법 제103조")

    assert result.returncode == 0
    payload = CitationRef.model_validate_json(result.stdout)
    assert payload.kind == "statute"
    assert payload.law == "민법"
    assert payload.jo == "제103조"


def test_korean_law_extract_hang_subcommand_accepts_stdin(repo_root: Path) -> None:
    article_text = (
        "제108조(통정한 허위의 의사표시)\n"
        "①상대방과 통정한 허위의 의사표시는 무효로 한다.\n"
        "②전항의 의사표시의 무효는 선의의 제삼자에게 대항하지 못한다.\n"
    )

    result = _run_module(repo_root, "korean_law", "extract-hang", "-", "2", input_text=article_text)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "선의의 제삼자에게" in payload["hang"]


def test_korean_law_extract_ho_subcommand_accepts_file(repo_root: Path, tmp_path: Path) -> None:
    hang_path = tmp_path / "hang.txt"
    hang_path.write_text(
        "개인정보처리자는 다음 각 호의 어느 하나에 해당하는 경우에는 ...\n"
        "1.  정보주체의 동의를 받은 경우\n"
        "2.  법률에 특별한 규정이 있거나 ...\n"
        "3.  공공기관이 법령 등에서 정하는 ...\n",
        encoding="utf-8",
    )

    result = _run_module(repo_root, "korean_law", "extract-ho", str(hang_path), "2")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "법률에 특별한 규정이 있거나" in payload["ho"]


def test_korean_law_normalize_case_subcommand(repo_root: Path) -> None:
    result = _run_module(repo_root, "korean_law", "normalize-case", "대법원-2023-다-302036")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {"normalized": "2023다302036"}


def test_korean_law_lookup_law_subcommand(repo_root: Path) -> None:
    result = _run_module(repo_root, "korean_law", "lookup-law", "개인정보 보호법")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {"law_id": "011357"}


def _write_docx(path: Path, body_xml: str) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body_xml}
  </w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
