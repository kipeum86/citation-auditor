"""citation_auditor package."""

from citation_auditor.aggregation import aggregate_verdicts
from citation_auditor.chunking import chunk_markdown, dedupe_claims
from citation_auditor.docx import extract_docx, write_docx_extraction
from citation_auditor.finalize import finalize_audit
from citation_auditor.models import (
    AggregateInput,
    AggregateOutput,
    AggregatedVerdict,
    AuditReason,
    Claim,
    ClaimList,
    ClaimType,
    ChunkOutput,
    ChunkPayload,
    ChunkSegmentPayload,
    Evidence,
    SentenceSpan,
    SourceBlock,
    SourceMap,
    Verdict,
    VerdictLabel,
)
from citation_auditor.prepare import prepare_audit
from citation_auditor.render import render_markdown
from citation_auditor.report import render_audit_report
from citation_auditor.settings import AuditSettings

__all__ = [
    "AggregateInput",
    "AggregateOutput",
    "AggregatedVerdict",
    "AuditReason",
    "AuditSettings",
    "Claim",
    "ClaimList",
    "ClaimType",
    "ChunkOutput",
    "ChunkPayload",
    "ChunkSegmentPayload",
    "Evidence",
    "SentenceSpan",
    "SourceBlock",
    "SourceMap",
    "Verdict",
    "VerdictLabel",
    "aggregate_verdicts",
    "chunk_markdown",
    "dedupe_claims",
    "extract_docx",
    "finalize_audit",
    "prepare_audit",
    "render_markdown",
    "render_audit_report",
    "write_docx_extraction",
]

__version__ = "1.4.0"
