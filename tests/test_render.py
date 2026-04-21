from citation_auditor.models import Claim, ClaimType, SentenceSpan, Verdict, VerdictLabel
from citation_auditor.render import render_markdown


def test_render_inserts_badges_in_reverse_order_and_skips_quote_and_code() -> None:
    md_text = (
        "Normal sentence one.\n\n"
        "> Quoted sentence should stay untouched.\n\n"
        "```\nCode sentence should stay untouched.\n```\n\n"
        "Normal sentence two."
    )
    quote_text = "Quoted sentence should stay untouched."
    code_text = "Code sentence should stay untouched."
    quote_start = md_text.index(quote_text)
    code_start = md_text.index(code_text)
    verdicts = [
        Verdict(
            claim=Claim(
                text="Normal sentence one.",
                sentence_span=SentenceSpan(start=0, end=len("Normal sentence one.")),
                claim_type=ClaimType.FACTUAL,
                suggested_verifier="general-web",
            ),
            label=VerdictLabel.CONTRADICTED,
            verifier_name="general-web",
            authority=0.5,
            rationale="Wrong.",
            evidence=[],
        ),
        Verdict(
            claim=Claim(
                text=quote_text,
                sentence_span=SentenceSpan(start=quote_start, end=quote_start + len(quote_text)),
                claim_type=ClaimType.FACTUAL,
                suggested_verifier="general-web",
            ),
            label=VerdictLabel.UNKNOWN,
            verifier_name="general-web",
            authority=0.5,
            rationale="Skip quote.",
            evidence=[],
        ),
        Verdict(
            claim=Claim(
                text=code_text,
                sentence_span=SentenceSpan(start=code_start, end=code_start + len(code_text)),
                claim_type=ClaimType.FACTUAL,
                suggested_verifier="general-web",
            ),
            label=VerdictLabel.UNKNOWN,
            verifier_name="general-web",
            authority=0.5,
            rationale="Skip code.",
            evidence=[],
        ),
        Verdict(
            claim=Claim(
                text="Normal sentence two.",
                sentence_span=SentenceSpan(start=len(md_text) - len("Normal sentence two."), end=len(md_text)),
                claim_type=ClaimType.FACTUAL,
                suggested_verifier="general-web",
            ),
            label=VerdictLabel.VERIFIED,
            verifier_name="general-web",
            authority=0.5,
            rationale="Right.",
            evidence=[],
        ),
    ]

    rendered = render_markdown(md_text, verdicts)

    assert "Normal sentence one. **[⚠️ general-web]**" in rendered
    assert "Normal sentence two. **[✅ general-web]**" in rendered
    assert "> Quoted sentence should stay untouched." in rendered
    code_section = rendered.split("```")[1]
    assert "**[❓ general-web]**" not in code_section

