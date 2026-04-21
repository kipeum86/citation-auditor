from citation_auditor.aggregation import aggregate_verdicts
from citation_auditor.models import Claim, ClaimType, SentenceSpan, Verdict, VerdictLabel


def _claim() -> Claim:
    return Claim(
        text="The claim under review.",
        sentence_span=SentenceSpan(start=10, end=31),
        claim_type=ClaimType.FACTUAL,
        suggested_verifier="general-web",
    )


def _verdict(label: VerdictLabel, verifier_name: str, authority: float) -> Verdict:
    claim = _claim()
    return Verdict(
        claim=claim,
        label=label,
        verifier_name=verifier_name,
        authority=authority,
        rationale=f"{verifier_name} says {label.value}.",
        evidence=[],
    )


def test_aggregate_single_verdict_passes_through() -> None:
    verdict = _verdict(VerdictLabel.VERIFIED, "general-web", 0.5)

    aggregated = aggregate_verdicts(_claim(), [verdict])

    assert aggregated == verdict


def test_aggregate_no_verdicts_returns_unknown_none() -> None:
    aggregated = aggregate_verdicts(_claim(), [])

    assert aggregated.label == VerdictLabel.UNKNOWN
    assert aggregated.verifier_name == "none"
    assert aggregated.authority == 0.0


def test_aggregate_higher_authority_wins() -> None:
    low = _verdict(VerdictLabel.VERIFIED, "general-web", 0.5)
    high = _verdict(VerdictLabel.CONTRADICTED, "korean-law", 1.0)

    aggregated = aggregate_verdicts(_claim(), [low, high])

    assert aggregated == high


def test_aggregate_same_authority_conflict_returns_unknown() -> None:
    first = _verdict(VerdictLabel.VERIFIED, "verifier-a", 1.0)
    second = _verdict(VerdictLabel.CONTRADICTED, "verifier-b", 1.0)

    aggregated = aggregate_verdicts(_claim(), [first, second])

    assert aggregated.label == VerdictLabel.UNKNOWN
    assert aggregated.verifier_name == "conflict"
    assert aggregated.authority == 1.0
