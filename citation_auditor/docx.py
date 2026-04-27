from __future__ import annotations

import json
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from citation_auditor.models import SourceBlock, SourceMap


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
NS = {"w": W_NS}

MAX_ZIP_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100


class DocxExtractionError(ValueError):
    """Raised when a DOCX cannot be safely converted into audit text."""


def extract_docx(path: Path, markdown_path: Path | None = None) -> tuple[str, SourceMap]:
    document_xml = _read_document_xml(path)
    root = ElementTree.fromstring(document_xml)
    body = root.find("w:body", NS)
    if body is None:
        raise DocxExtractionError("DOCX does not contain word/document.xml body")

    extracted_blocks = _extract_body_blocks(body)
    markdown_text, blocks = _build_markdown_and_blocks(extracted_blocks)
    source_map = SourceMap(
        source_type="docx",
        source_path=str(path),
        markdown_path=str(markdown_path) if markdown_path is not None else None,
        blocks=blocks,
    )
    return markdown_text, source_map


def write_docx_extraction(input_docx: Path, out_md: Path, out_map: Path) -> dict[str, str]:
    markdown_text, source_map = extract_docx(input_docx, markdown_path=out_md)
    out_md.write_text(markdown_text, encoding="utf-8")
    out_map.write_text(source_map.model_dump_json(indent=2), encoding="utf-8")
    return {"markdown": str(out_md), "map": str(out_map)}


def _read_document_xml(path: Path) -> bytes:
    try:
        with zipfile.ZipFile(path) as archive:
            _validate_archive(archive)
            try:
                return archive.read("word/document.xml")
            except KeyError as exc:
                raise DocxExtractionError("DOCX is missing word/document.xml") from exc
    except zipfile.BadZipFile as exc:
        raise DocxExtractionError("Input is not a valid DOCX zip archive") from exc


def _validate_archive(archive: zipfile.ZipFile) -> None:
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise DocxExtractionError("DOCX contains too many zip entries")

    total_uncompressed = 0
    total_compressed = 0
    for info in infos:
        _validate_zip_name(info.filename)
        total_uncompressed += info.file_size
        total_compressed += info.compress_size

    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise DocxExtractionError("DOCX uncompressed size exceeds the safety limit")

    if total_compressed > 0 and total_uncompressed / total_compressed > MAX_COMPRESSION_RATIO:
        raise DocxExtractionError("DOCX compression ratio exceeds the safety limit")


def _validate_zip_name(name: str) -> None:
    normalized = posixpath.normpath(name.replace("\\", "/"))
    if "\x00" in name or posixpath.isabs(normalized) or normalized == ".." or normalized.startswith("../"):
        raise DocxExtractionError(f"Unsafe DOCX zip entry: {name}")


def _extract_body_blocks(body: ElementTree.Element) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    paragraph_index = 0
    table_index = 0

    for child in body:
        if child.tag == W + "p":
            text = _paragraph_text(child).strip()
            if not text:
                continue
            paragraph_index += 1
            kind = "list_item" if child.find("w:pPr/w:numPr", NS) is not None else "paragraph"
            blocks.append((kind, text))
        elif child.tag == W + "tbl":
            table_index += 1
            blocks.extend(_extract_table_blocks(child, table_index))

    return blocks


def _extract_table_blocks(table: ElementTree.Element, table_index: int) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for row_index, row in enumerate(table.findall("w:tr", NS), start=1):
        for cell_index, cell in enumerate(row.findall("w:tc", NS), start=1):
            text = _cell_text(cell).strip()
            if not text:
                continue
            blocks.append((f"table_cell:{table_index}:{row_index}:{cell_index}", text))
    return blocks


def _cell_text(cell: ElementTree.Element) -> str:
    paragraphs: list[str] = []
    for paragraph in cell.findall(".//w:p", NS):
        text = _paragraph_text(paragraph).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []
    _collect_text(paragraph, parts, in_deleted=False)
    return "".join(parts)


def _collect_text(element: ElementTree.Element, parts: list[str], *, in_deleted: bool) -> None:
    deleted = in_deleted or element.tag == W + "del"
    if deleted:
        return

    if element.tag == W + "t":
        parts.append(element.text or "")
    elif element.tag == W + "tab":
        parts.append("\t")
    elif element.tag in {W + "br", W + "cr"}:
        parts.append("\n")

    for child in element:
        _collect_text(child, parts, in_deleted=deleted)


def _build_markdown_and_blocks(extracted_blocks: list[tuple[str, str]]) -> tuple[str, list[SourceBlock]]:
    parts: list[str] = []
    blocks: list[SourceBlock] = []
    paragraph_count = 0
    offset = 0

    for raw_kind, text in extracted_blocks:
        if parts:
            parts.append("\n\n")
            offset += 2
        start = offset
        parts.append(text)
        end = start + len(text)
        offset = end

        if raw_kind in {"paragraph", "list_item"}:
            paragraph_count += 1
        kind, block_id, label = _block_identity(raw_kind, paragraph_count)

        blocks.append(SourceBlock(id=block_id, kind=kind, label=label, text=text, start=start, end=end))

    return "".join(parts), blocks


def _block_identity(raw_kind: str, paragraph_count: int) -> tuple[str, str, str]:
    if raw_kind.startswith("table_cell:"):
        _, table, row, cell = raw_kind.split(":")
        table_num = int(table)
        row_num = int(row)
        cell_num = int(cell)
        return (
            "table_cell",
            f"T{table_num:03d}R{row_num:02d}C{cell_num:02d}",
            f"표 {table_num} / 행 {row_num} / 열 {cell_num}",
        )
    if raw_kind == "list_item":
        return "list_item", f"P{paragraph_count:04d}", f"문단 {paragraph_count}"
    return "paragraph", f"P{paragraph_count:04d}", f"문단 {paragraph_count}"


def source_map_from_json(text: str) -> SourceMap:
    return SourceMap.model_validate_json(text)


def source_map_to_json(source_map: SourceMap) -> str:
    return json.dumps(source_map.model_dump(mode="json"), ensure_ascii=False, indent=2)
