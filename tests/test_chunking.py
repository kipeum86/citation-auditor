from citation_auditor.chunking import chunk_markdown, dedupe_claims
from citation_auditor.models import Claim, ClaimType, SentenceSpan


def test_chunk_markdown_preserves_block_boundaries_with_overlap() -> None:
    md_text = (
        "P1.\n\n"
        "Para two has enough words to trigger overlap.\n\n"
        "Para three lands in the next chunk."
    )

    chunks = chunk_markdown(md_text, max_tokens=20)

    assert len(chunks) >= 2
    assert "Para two has enough words to trigger overlap." in chunks[0].text
    assert chunks[1].text.startswith("Para two has enough words to trigger overlap.")


def test_dedupe_claims_uses_text_and_nearby_offsets() -> None:
    claims = [
        Claim(
            text="The Paris Agreement was adopted in 2015.",
            sentence_span=SentenceSpan(start=100, end=139),
            claim_type=ClaimType.FACTUAL,
            suggested_verifier="general-web",
        ),
        Claim(
            text="The Paris Agreement was adopted in 2015.",
            sentence_span=SentenceSpan(start=112, end=151),
            claim_type=ClaimType.FACTUAL,
            suggested_verifier="general-web",
        ),
        Claim(
            text="The United Nations was founded in 1945.",
            sentence_span=SentenceSpan(start=300, end=338),
            claim_type=ClaimType.FACTUAL,
            suggested_verifier="general-web",
        ),
    ]

    deduped = dedupe_claims(claims)

    assert len(deduped) == 2
