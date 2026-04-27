from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any


class PrepareError(ValueError):
    """Raised when an audit run cannot be safely prepared."""


def prepare_audit(input_path: Path, *, overwrite: bool = False) -> dict[str, Any]:
    source_path = input_path.expanduser().resolve()
    if not source_path.exists():
        raise PrepareError(f"Input file does not exist: {input_path}")
    if not source_path.is_file():
        raise PrepareError(f"Input path is not a file: {input_path}")

    suffix = source_path.suffix.lower()
    if suffix not in {".md", ".markdown", ".docx"}:
        raise PrepareError("Input must have extension .md, .markdown, or .docx")

    mode = "docx_report" if suffix == ".docx" else "markdown"
    report_md = source_path.with_name(f"{source_path.stem}.audit.md") if mode == "docx_report" else None
    report_json = source_path.with_name(f"{source_path.stem}.audit.json") if mode == "docx_report" else None
    _guard_outputs([path for path in (report_md, report_json) if path is not None], overwrite=overwrite)

    work_dir = Path(tempfile.mkdtemp(prefix=f"citation-auditor-{_safe_stem(source_path.stem)}-"))
    audit_source = work_dir / f"{_safe_stem(source_path.stem)}.audit-source.md" if mode == "docx_report" else None
    source_map = work_dir / f"{_safe_stem(source_path.stem)}.map.json" if mode == "docx_report" else None
    audit_input = audit_source if audit_source is not None else source_path

    return {
        "mode": mode,
        "source_type": "docx" if mode == "docx_report" else "markdown",
        "source_path": str(source_path),
        "audit_input": str(audit_input),
        "work_dir": str(work_dir),
        "overwrite": overwrite,
        "paths": {
            "audit_source_md": str(audit_source) if audit_source is not None else None,
            "source_map_json": str(source_map) if source_map is not None else None,
            "aggregate_input_json": str(work_dir / "aggregate-input.json"),
            "aggregate_output_json": str(work_dir / "aggregated.json"),
            "report_md": str(report_md) if report_md is not None else None,
            "report_json": str(report_json) if report_json is not None else None,
        },
    }


def _guard_outputs(paths: list[Path], *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        joined = ", ".join(existing)
        raise PrepareError(f"Output file already exists: {joined}. Rerun with --overwrite to replace it.")


def _safe_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return safe or "input"
