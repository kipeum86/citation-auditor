import zipfile
from pathlib import Path

import pytest

from citation_auditor.chunking import chunk_markdown
from citation_auditor.docx import DocxExtractionError, extract_docx


def test_extract_docx_paragraphs_and_tables(tmp_path: Path) -> None:
    docx_path = tmp_path / "input.docx"
    _write_docx(
        docx_path,
        """
        <w:p><w:r><w:t>민법 제103조는 반사회질서 법률행위를 무효로 한다.</w:t></w:r></w:p>
        <w:tbl>
          <w:tr>
            <w:tc><w:p><w:r><w:t>표 안의 개인정보 보호법 제15조 인용.</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>두 번째 셀.</w:t></w:r></w:p></w:tc>
          </w:tr>
        </w:tbl>
        """,
    )

    markdown, source_map = extract_docx(docx_path)

    assert "민법 제103조는 반사회질서 법률행위를 무효로 한다." in markdown
    assert "표 안의 개인정보 보호법 제15조 인용." in markdown
    assert [block.label for block in source_map.blocks] == ["문단 1", "표 1 / 행 1 / 열 1", "표 1 / 행 1 / 열 2"]
    for block in source_map.blocks:
        assert markdown[block.start : block.end] == block.text


def test_extract_docx_ignores_empty_and_deleted_text(tmp_path: Path) -> None:
    docx_path = tmp_path / "input.docx"
    _write_docx(
        docx_path,
        """
        <w:p><w:r><w:t></w:t></w:r></w:p>
        <w:p>
          <w:del><w:r><w:t>삭제된 잘못된 인용.</w:t></w:r></w:del>
          <w:ins><w:r><w:t>삽입된 현재 본문.</w:t></w:r></w:ins>
        </w:p>
        """,
    )

    markdown, source_map = extract_docx(docx_path)

    assert "삭제된 잘못된 인용" not in markdown
    assert markdown == "삽입된 현재 본문."
    assert len(source_map.blocks) == 1


def test_chunk_offsets_align_with_docx_blocks(tmp_path: Path) -> None:
    docx_path = tmp_path / "input.docx"
    _write_docx(
        docx_path,
        """
        <w:p><w:r><w:t>첫 번째 문단.</w:t></w:r></w:p>
        <w:p><w:r><w:t>두 번째 문단.</w:t></w:r></w:p>
        <w:p><w:r><w:t>세 번째 문단.</w:t></w:r></w:p>
        """,
    )
    markdown, source_map = extract_docx(docx_path)

    chunks = chunk_markdown(markdown, max_tokens=5)
    block_spans = {(block.start, block.end) for block in source_map.blocks}

    assert chunks
    for chunk in chunks:
        for segment in chunk.segments:
            assert (segment.document_start, segment.document_end) in block_spans


def test_extract_docx_rejects_unsafe_zip_entry(tmp_path: Path) -> None:
    docx_path = tmp_path / "bad.docx"
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr("../word/document.xml", "<xml />")

    with pytest.raises(DocxExtractionError):
        extract_docx(docx_path)


def _write_docx(path: Path, body_xml: str) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body_xml}
  </w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
