from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citation_auditor.models import AggregateOutput, SourceBlock, SourceMap, Verdict, VerdictLabel


SEVERITY_ORDER = {
    VerdictLabel.CONTRADICTED: 0,
    VerdictLabel.UNKNOWN: 1,
    VerdictLabel.VERIFIED: 2,
}


def build_audit_report_payload(
    source_map: SourceMap,
    aggregate_output: AggregateOutput,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or _utc_timestamp()
    ordered = _ordered_verdicts(aggregate_output)
    summary = _summary_counts([item.verdict for item in aggregate_output.aggregated])

    return {
        "source": {
            "type": source_map.source_type,
            "path": source_map.source_path,
            "markdown_path": source_map.markdown_path,
        },
        "generated": generated,
        "mode": "external_report",
        "scope": {
            "audited_content": _audited_content(source_map),
            "omissions": list(source_map.omissions),
        },
        "summary": summary,
        "findings": [
            _finding_payload(f"C-{finding_index:03d}", source_map, verdict)
            for finding_index, (_, verdict) in enumerate(ordered, start=1)
        ],
    }


def render_audit_report(source_map: SourceMap, aggregate_output: AggregateOutput, *, generated_at: str | None = None) -> str:
    payload = build_audit_report_payload(source_map, aggregate_output, generated_at=generated_at)
    return _render_audit_report_payload(payload)


def write_audit_report(
    source_map_path: Path,
    aggregate_path: Path,
    out_path: Path | None = None,
    out_json_path: Path | None = None,
) -> str:
    source_map = SourceMap.model_validate_json(source_map_path.read_text(encoding="utf-8"))
    aggregate_output = AggregateOutput.model_validate_json(aggregate_path.read_text(encoding="utf-8"))
    generated_at = _utc_timestamp()
    payload = build_audit_report_payload(source_map, aggregate_output, generated_at=generated_at)
    report = _render_audit_report_payload(payload)
    if out_path is not None:
        out_path.write_text(report, encoding="utf-8")
    if out_json_path is not None:
        out_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _render_audit_report_payload(payload: dict[str, Any]) -> str:
    source = payload["source"]
    summary = payload["summary"]
    findings = payload["findings"]
    lines = [
        "# Citation Audit Report",
        "",
        f"- Source: {source['path']}",
        f"- Generated: {payload['generated']}",
        "- Mode: external report",
        "",
        "## Scope Notice",
        "",
        *_scope_notice_lines(payload["scope"]),
        "",
        "## Summary",
        "",
        "| Verdict | Count |",
        "|---|---:|",
        f"| contradicted | {summary['contradicted']} |",
        f"| unknown | {summary['unknown']} |",
        f"| verified | {summary['verified']} |",
        "",
        "## Findings",
        "",
        "| ID | Verdict | Location | Verifier | Claim |",
        "|---|---|---|---|---|",
    ]

    if not findings:
        lines.append("| - | - | - | - | No claims audited. |")
    else:
        for finding in findings:
            lines.append(
                "| {id} | {label} | {location} | {verifier} | {claim} |".format(
                    id=finding["id"],
                    label=_escape_table(finding["label"]),
                    location=_escape_table(finding["location"]),
                    verifier=_escape_table(finding["verifier"]),
                    claim=_escape_table(_truncate(finding["claim"])),
                )
            )

    lines.extend(["", "## Details", ""])
    if not findings:
        lines.append("No claims were audited.")
    else:
        for finding in findings:
            lines.extend(_detail_lines(finding))

    return "\n".join(lines).rstrip() + "\n"


def _detail_lines(finding: dict[str, Any]) -> list[str]:
    lines = [
        f"### {finding['id']}",
        "",
        f"- Verdict: {finding['label']}",
        f"- Location: {finding['location']}",
        f"- Verifier: {finding['verifier']}",
        f"- Claim: {finding['claim']}",
        f"- Rationale: {finding['rationale']}",
    ]
    if finding["evidence"]:
        lines.append("- Evidence:")
        for evidence in finding["evidence"]:
            lines.append(f"  - {_format_evidence(evidence.get('title'), evidence['url'])}")
    else:
        lines.append("- Evidence: none")
    lines.append("")
    return lines


def _ordered_verdicts(aggregate_output: AggregateOutput) -> list[tuple[int, Verdict]]:
    verdicts = [item.verdict for item in aggregate_output.aggregated]
    return sorted(
        enumerate(verdicts, start=1),
        key=lambda item: (
            SEVERITY_ORDER.get(item[1].label, 99),
            item[1].claim.sentence_span.start,
            item[0],
        ),
    )


def _summary_counts(verdicts: list[Verdict]) -> dict[str, int]:
    counts = Counter(verdict.label for verdict in verdicts)
    return {
        "contradicted": counts[VerdictLabel.CONTRADICTED],
        "unknown": counts[VerdictLabel.UNKNOWN],
        "verified": counts[VerdictLabel.VERIFIED],
        "total": len(verdicts),
    }


def _finding_payload(finding_id: str, source_map: SourceMap, verdict: Verdict) -> dict[str, Any]:
    return {
        "id": finding_id,
        "label": verdict.label.value,
        "location": _location_for_verdict(source_map, verdict),
        "verifier": verdict.verifier_name,
        "authority": verdict.authority,
        "claim": verdict.claim.text,
        "claim_type": verdict.claim.claim_type.value,
        "audit_reason": verdict.claim.audit_reason.value if verdict.claim.audit_reason is not None else None,
        "sentence_span": verdict.claim.sentence_span.model_dump(mode="json"),
        "rationale": verdict.rationale,
        "evidence": [evidence.model_dump(mode="json") for evidence in verdict.evidence],
    }


def _scope_notice_lines(scope: dict[str, Any]) -> list[str]:
    lines = [f"- Audited content: {scope['audited_content']}"]
    omissions = scope["omissions"]
    if omissions:
        lines.append("- Not audited or partially represented:")
        for omission in omissions:
            lines.append(f"  - {omission}")
    else:
        lines.append("- No extraction omissions were recorded.")
    return lines


def _audited_content(source_map: SourceMap) -> str:
    if source_map.source_type == "docx":
        return "DOCX body paragraphs and table cells extracted from `word/document.xml`."
    return f"`{source_map.source_type}` text source."


def _location_for_verdict(source_map: SourceMap, verdict: Verdict) -> str:
    start = verdict.claim.sentence_span.start
    end = verdict.claim.sentence_span.end
    block = _block_for_offset(source_map.blocks, start)
    if block is None:
        return "위치 미상"
    if end > block.end:
        return f"{block.label} (이어짐)"
    return block.label


def _block_for_offset(blocks: list[SourceBlock], offset: int) -> SourceBlock | None:
    return next((block for block in blocks if block.start <= offset < block.end), None)


def _format_evidence(title: str | None, reference: str) -> str:
    if title and title != reference:
        return f"{title} ({reference})"
    return reference


def _escape_table(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _truncate(value: str, limit: int = 180) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
