from citation_auditor.models import AuditReason, Claim, ClaimType, SentenceSpan


def test_claim_accepts_optional_audit_reason() -> None:
    claim = Claim(
        text="2024년부터 시행된다.",
        sentence_span=SentenceSpan(start=0, end=11),
        claim_type=ClaimType.TEMPORAL,
        suggested_verifier="general-web",
        audit_reason=AuditReason.TEMPORAL,
    )

    assert claim.audit_reason == AuditReason.TEMPORAL


def test_claim_keeps_audit_reason_optional_for_legacy_payloads() -> None:
    claim = Claim(
        text="민법 제103조 인용.",
        sentence_span=SentenceSpan(start=0, end=11),
        claim_type=ClaimType.CITATION,
        suggested_verifier="korean-law",
    )

    assert claim.audit_reason is None
