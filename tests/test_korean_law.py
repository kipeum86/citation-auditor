from citation_auditor.korean_law import (
    LAW_ID_LOOKUP,
    circled_digit_to_int,
    extract_hang,
    extract_ho,
    normalize_case_number,
    parse_citation,
)


PERSONAL_INFO_PROTECTION_ARTICLE_15 = """제15조(개인정보의 수집ㆍ이용)
① 개인정보처리자는 다음 각 호의 어느 하나에 해당하는 경우에는 ...
1.  정보주체의 동의를 받은 경우
2.  법률에 특별한 규정이 있거나 ...
3.  공공기관이 법령 등에서 정하는 ...
4.  정보주체와 체결한 계약을 ...
5.  명백히 정보주체 또는 제3자의 ...
6.  개인정보처리자의 정당한 이익을 ...
7.  공중위생 등 공공의 안전과 안녕을 ...
② 개인정보처리자는 제1항제1호에 따른 동의를 받을 때에는 ...
1.  개인정보의 수집ㆍ이용 목적
2.  수집하려는 개인정보의 항목
...
③ 개인정보처리자는 당초 수집 목적과 ..."""

MINBEOB_ARTICLE_108 = """제108조(통정한 허위의 의사표시)
①상대방과 통정한 허위의 의사표시는 무효로 한다.
②전항의 의사표시의 무효는 선의의 제삼자에게 대항하지 못한다."""

MINBEOB_ARTICLE_103 = """제103조 반사회질서의 법률행위
선량한 풍속 기타 사회질서에 위반한 사항을 내용으로 하는 법률행위는 무효로 한다."""


def test_law_id_lookup_contains_verified_aliases() -> None:
    assert LAW_ID_LOOKUP["민법"] == "001706"
    assert LAW_ID_LOOKUP["개인정보 보호법"] == "011357"
    assert LAW_ID_LOOKUP["개인정보보호법"] == "011357"


def test_extract_hang_handles_article_with_hang_and_ho() -> None:
    first = extract_hang(PERSONAL_INFO_PROTECTION_ARTICLE_15, 1)
    third = extract_hang(PERSONAL_INFO_PROTECTION_ARTICLE_15, 3)

    assert first is not None
    assert third is not None
    assert "정보주체의 동의를 받은 경우" in first
    assert "당초 수집 목적과" in third


def test_extract_ho_handles_numbered_items() -> None:
    first_hang = extract_hang(PERSONAL_INFO_PROTECTION_ARTICLE_15, 1)
    assert first_hang is not None

    second_ho = extract_ho(first_hang, 2)

    assert second_ho is not None
    assert "법률에 특별한 규정이 있거나" in second_ho


def test_extract_hang_handles_article_with_hang_but_no_ho() -> None:
    first = extract_hang(MINBEOB_ARTICLE_108, 1)
    second = extract_hang(MINBEOB_ARTICLE_108, 2)

    assert first is not None
    assert second is not None
    assert "상대방과 통정한 허위의" in first
    assert "선의의 제삼자에게" in second


def test_extract_hang_returns_none_for_single_paragraph_article() -> None:
    assert extract_hang(MINBEOB_ARTICLE_103, 1) is None


def test_parse_citation_handles_statute_article_only() -> None:
    citation = parse_citation("민법 제103조")

    assert citation.kind == "statute"
    assert citation.law == "민법"
    assert citation.jo == "제103조"
    assert citation.hang is None
    assert citation.ho is None
    assert citation.case_number is None


def test_parse_citation_handles_statute_article_hang_ho() -> None:
    citation = parse_citation("개인정보 보호법 제15조 제1항 제2호")

    assert citation.kind == "statute"
    assert citation.law == "개인정보 보호법"
    assert citation.jo == "제15조"
    assert citation.hang == 1
    assert citation.ho == 2
    assert citation.case_number is None


def test_parse_citation_handles_precedent_with_court_prefix() -> None:
    citation = parse_citation("대법원 2023다302036")

    assert citation.kind == "precedent"
    assert citation.case_number == "2023다302036"
    assert citation.law is None
    assert citation.jo is None


def test_parse_citation_handles_precedent_without_court_prefix() -> None:
    citation = parse_citation("2023다302036")

    assert citation.kind == "precedent"
    assert citation.case_number == "2023다302036"
    assert citation.law is None
    assert citation.jo is None


def test_normalize_case_number_handles_dashed_court_format() -> None:
    assert normalize_case_number("대법원-2023-다-302036") == "2023다302036"


def test_circled_digit_to_int_maps_supported_range() -> None:
    assert circled_digit_to_int("①") == 1
    assert circled_digit_to_int("⑳") == 20
    assert circled_digit_to_int("A") is None
