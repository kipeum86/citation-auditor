from citation_auditor.models import (
    AggregateOutput,
    AggregatedVerdict,
    Claim,
    ClaimType,
    Evidence,
    SentenceSpan,
    SourceBlock,
    SourceMap,
    Verdict,
    VerdictLabel,
)
from citation_auditor.report import build_audit_report_payload, render_audit_report


def test_report_renders_summary_counts_and_locations() -> None:
    source_map = SourceMap(
        source_type="docx",
        source_path="opinion.docx",
        markdown_path="/tmp/opinion.md",
        blocks=[
            SourceBlock(id="P0001", kind="paragraph", label="문단 1", text="Alpha claim.", start=0, end=12),
            SourceBlock(id="P0002", kind="paragraph", label="문단 2", text="Beta claim.", start=14, end=25),
        ],
    )
    aggregate_output = AggregateOutput(
        aggregated=[
            AggregatedVerdict(
                claim=_claim("Alpha claim.", 0, 12),
                verdict=Verdict(
                    claim=_claim("Alpha claim.", 0, 12),
                    label=VerdictLabel.VERIFIED,
                    verifier_name="general-web",
                    authority=0.5,
                    rationale="Checked.",
                    evidence=[],
                ),
            ),
            AggregatedVerdict(
                claim=_claim("Beta claim.", 14, 25),
                verdict=Verdict(
                    claim=_claim("Beta claim.", 14, 25),
                    label=VerdictLabel.CONTRADICTED,
                    verifier_name="korean-law",
                    authority=1.0,
                    rationale="Contradicted.",
                    evidence=[Evidence(url="https://example.com", title="Example")],
                ),
            ),
        ]
    )

    report = render_audit_report(source_map, aggregate_output, generated_at="2026-04-26T00:00:00Z")

    assert "## Scope Notice" in report
    assert "Audited content: DOCX body paragraphs and table cells" in report
    assert "No extraction omissions were recorded." in report
    assert "| contradicted | 1 |" in report
    assert "| unknown | 0 |" in report
    assert "| verified | 1 |" in report
    assert "| C-001 | contradicted | 문단 2 | korean-law | Beta claim. |" in report
    assert "| C-002 | verified | 문단 1 | general-web | Alpha claim. |" in report
    assert "Example (https://example.com)" in report


def test_report_marks_unknown_and_cross_block_locations() -> None:
    source_map = SourceMap(
        source_type="docx",
        source_path="opinion.docx",
        blocks=[
            SourceBlock(id="P0001", kind="paragraph", label="문단 1", text="Alpha", start=0, end=5),
            SourceBlock(id="P0002", kind="paragraph", label="문단 2", text="Beta", start=7, end=11),
        ],
    )
    aggregate_output = AggregateOutput(
        aggregated=[
            AggregatedVerdict(
                claim=_claim("spans separator", 5, 7),
                verdict=Verdict(
                    claim=_claim("spans separator", 5, 7),
                    label=VerdictLabel.UNKNOWN,
                    verifier_name="general-web",
                    authority=0.5,
                    rationale="No block.",
                    evidence=[],
                ),
            ),
            AggregatedVerdict(
                claim=_claim("crosses blocks", 3, 9),
                verdict=Verdict(
                    claim=_claim("crosses blocks", 3, 9),
                    label=VerdictLabel.CONTRADICTED,
                    verifier_name="general-web",
                    authority=0.5,
                    rationale="Crosses.",
                    evidence=[],
                ),
            ),
        ]
    )

    report = render_audit_report(source_map, aggregate_output, generated_at="2026-04-26T00:00:00Z")

    assert "문단 1 (이어짐)" in report
    assert "위치 미상" in report


def test_report_includes_scope_omissions() -> None:
    source_map = SourceMap(
        source_type="docx",
        source_path="opinion.docx",
        omissions=["Footnotes were detected but were not extracted in this version."],
        blocks=[SourceBlock(id="P0001", kind="paragraph", label="문단 1", text="Alpha", start=0, end=5)],
    )
    aggregate_output = AggregateOutput(aggregated=[])

    report = render_audit_report(source_map, aggregate_output, generated_at="2026-04-26T00:00:00Z")

    assert "- Not audited or partially represented:" in report
    assert "Footnotes were detected but were not extracted in this version." in report


def test_report_payload_contains_machine_readable_findings() -> None:
    source_map = SourceMap(
        source_type="docx",
        source_path="opinion.docx",
        markdown_path="/tmp/opinion.audit-source.md",
        omissions=["Comments were detected but were not extracted in this version."],
        blocks=[SourceBlock(id="P0001", kind="paragraph", label="문단 1", text="Alpha claim.", start=0, end=12)],
    )
    aggregate_output = AggregateOutput(
        aggregated=[
            AggregatedVerdict(
                claim=_claim("Alpha claim.", 0, 12),
                verdict=Verdict(
                    claim=_claim("Alpha claim.", 0, 12),
                    label=VerdictLabel.CONTRADICTED,
                    verifier_name="korean-law",
                    authority=1.0,
                    rationale="The cited law does not support the claim.",
                    evidence=[Evidence(url="https://example.com/law", title="Law", snippet="Relevant excerpt.")],
                ),
            )
        ]
    )

    payload = build_audit_report_payload(source_map, aggregate_output, generated_at="2026-04-26T00:00:00Z")

    assert payload["source"] == {
        "type": "docx",
        "path": "opinion.docx",
        "markdown_path": "/tmp/opinion.audit-source.md",
    }
    assert payload["generated"] == "2026-04-26T00:00:00Z"
    assert payload["mode"] == "external_report"
    assert payload["summary"] == {"contradicted": 1, "unknown": 0, "verified": 0, "total": 1}
    assert payload["scope"]["omissions"] == ["Comments were detected but were not extracted in this version."]
    assert payload["findings"] == [
        {
            "id": "C-001",
            "label": "contradicted",
            "location": "문단 1",
            "verifier": "korean-law",
            "authority": 1.0,
            "claim": "Alpha claim.",
            "claim_type": "factual",
            "audit_reason": None,
            "sentence_span": {"start": 0, "end": 12},
            "rationale": "The cited law does not support the claim.",
            "evidence": [
                {
                    "url": "https://example.com/law",
                    "title": "Law",
                    "snippet": "Relevant excerpt.",
                    "extracted_text": None,
                }
            ],
        }
    ]


def _claim(text: str, start: int, end: int) -> Claim:
    return Claim(
        text=text,
        sentence_span=SentenceSpan(start=start, end=end),
        claim_type=ClaimType.FACTUAL,
        suggested_verifier="general-web",
    )
