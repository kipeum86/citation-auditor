from pathlib import Path

from citation_auditor.docx import extract_docx


def test_v14_docx_legal_fixture_extracts_expected_blocks(repo_root: Path) -> None:
    markdown, source_map = extract_docx(repo_root / "fixtures" / "v1.4-docx-legal.docx")

    expected_blocks = [
        ("paragraph", "문단 1", "민법 제103조는 선량한 풍속 기타 사회질서에 반하는 법률행위를 무효로 한다."),
        ("paragraph", "문단 2", "민법 제2000조는 AI 계약의 전자서명을 일률적으로 무효로 한다."),
        ("paragraph", "문단 3", "GDPR Article 17 recognizes a data subject's right to erasure."),
        ("paragraph", "문단 4", "업계 관계자에 따르면 AI 규제는 곧 완화될 전망이다."),
        ("table_cell", "표 1 / 행 1 / 열 1", "개인정보 보호법 제15조는 개인정보 처리의 법적 근거 중 정보주체 동의를 규정한다."),
        ("table_cell", "표 1 / 행 1 / 열 2", "개인정보 보호법 제88조는 청소년 유해매체물 등급분류 기준을 정한다."),
        ("table_cell", "표 1 / 행 2 / 열 1", "2023년 국내 게임산업 매출은 전년 대비 15% 증가했다."),
        ("table_cell", "표 1 / 행 2 / 열 2", "The EU AI Act was adopted in 2024."),
    ]

    assert [(block.kind, block.label, block.text) for block in source_map.blocks] == expected_blocks
    assert markdown == "\n\n".join(block_text for _, _, block_text in expected_blocks)
    for block in source_map.blocks:
        assert markdown[block.start : block.end] == block.text
