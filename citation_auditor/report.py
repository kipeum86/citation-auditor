from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from citation_auditor.models import AggregateOutput, SourceBlock, SourceMap, Verdict, VerdictLabel


SEVERITY_ORDER = {
    VerdictLabel.CONTRADICTED: 0,
    VerdictLabel.UNKNOWN: 1,
    VerdictLabel.VERIFIED: 2,
}


def render_audit_report(source_map: SourceMap, aggregate_output: AggregateOutput, *, generated_at: str | None = None) -> str:
    generated = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    verdicts = [item.verdict for item in aggregate_output.aggregated]
    ordered = sorted(
        enumerate(verdicts, start=1),
        key=lambda item: (
            SEVERITY_ORDER.get(item[1].label, 99),
            item[1].claim.sentence_span.start,
            item[0],
        ),
    )
    counts = Counter(verdict.label for verdict in verdicts)

    lines = [
        "# Citation Audit Report",
        "",
        f"- Source: {source_map.source_path}",
        f"- Generated: {generated}",
        "- Mode: external report",
        "",
        "## Scope Notice",
        "",
        *_scope_notice_lines(source_map),
        "",
        "## Summary",
        "",
        "| Verdict | Count |",
        "|---|---:|",
        f"| contradicted | {counts[VerdictLabel.CONTRADICTED]} |",
        f"| unknown | {counts[VerdictLabel.UNKNOWN]} |",
        f"| verified | {counts[VerdictLabel.VERIFIED]} |",
        "",
        "## Findings",
        "",
        "| ID | Verdict | Location | Verifier | Claim |",
        "|---|---|---|---|---|",
    ]

    if not ordered:
        lines.append("| - | - | - | - | No claims audited. |")
    else:
        for finding_index, (_, verdict) in enumerate(ordered, start=1):
            lines.append(
                "| {id} | {label} | {location} | {verifier} | {claim} |".format(
                    id=f"C-{finding_index:03d}",
                    label=_escape_table(verdict.label.value),
                    location=_escape_table(_location_for_verdict(source_map, verdict)),
                    verifier=_escape_table(verdict.verifier_name),
                    claim=_escape_table(_truncate(verdict.claim.text)),
                )
            )

    lines.extend(["", "## Details", ""])
    if not ordered:
        lines.append("No claims were audited.")
    else:
        for finding_index, (_, verdict) in enumerate(ordered, start=1):
            lines.extend(_detail_lines(f"C-{finding_index:03d}", source_map, verdict))

    return "\n".join(lines).rstrip() + "\n"


def write_audit_report(source_map_path: Path, aggregate_path: Path, out_path: Path | None = None) -> str:
    source_map = SourceMap.model_validate_json(source_map_path.read_text(encoding="utf-8"))
    aggregate_output = AggregateOutput.model_validate_json(aggregate_path.read_text(encoding="utf-8"))
    report = render_audit_report(source_map, aggregate_output)
    if out_path is not None:
        out_path.write_text(report, encoding="utf-8")
    return report


def _detail_lines(finding_id: str, source_map: SourceMap, verdict: Verdict) -> list[str]:
    lines = [
        f"### {finding_id}",
        "",
        f"- Verdict: {verdict.label.value}",
        f"- Location: {_location_for_verdict(source_map, verdict)}",
        f"- Verifier: {verdict.verifier_name}",
        f"- Claim: {verdict.claim.text}",
        f"- Rationale: {verdict.rationale}",
    ]
    if verdict.evidence:
        lines.append("- Evidence:")
        for evidence in verdict.evidence:
            lines.append(f"  - {_format_evidence(evidence.title, evidence.url)}")
    else:
        lines.append("- Evidence: none")
    lines.append("")
    return lines


def _scope_notice_lines(source_map: SourceMap) -> list[str]:
    lines: list[str] = []
    if source_map.source_type == "docx":
        lines.append("- Audited content: DOCX body paragraphs and table cells extracted from `word/document.xml`.")
    else:
        lines.append(f"- Audited content: `{source_map.source_type}` text source.")

    if source_map.omissions:
        lines.append("- Not audited or partially represented:")
        for omission in source_map.omissions:
            lines.append(f"  - {omission}")
    else:
        lines.append("- No extraction omissions were recorded.")
    return lines


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
