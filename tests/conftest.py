from __future__ import annotations

from pathlib import Path

import pytest

from citation_auditor.models import Claim, ClaimType, SentenceSpan


def sentence_span(text: str, sentence: str) -> SentenceSpan:
    start = text.index(sentence)
    return SentenceSpan(start=start, end=start + len(sentence))


def make_claim(text: str, document: str, *, claim_type: ClaimType = ClaimType.FACTUAL) -> Claim:
    return Claim(text=text, sentence_span=sentence_span(document, text), claim_type=claim_type, suggested_verifier="general-web")


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
