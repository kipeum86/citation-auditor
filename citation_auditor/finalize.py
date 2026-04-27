from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citation_auditor.models import AggregateOutput
from citation_auditor.render import render_markdown
from citation_auditor.report import write_audit_report


class FinalizeError(ValueError):
    """Raised when an audit run cannot be safely finalized."""


def finalize_audit(prepare_manifest_path: Path, aggregate_path: Path) -> str | dict[str, Any]:
    manifest = _load_manifest(prepare_manifest_path)
    mode = manifest.get("mode")
    paths = manifest.get("paths")
    if not isinstance(paths, dict):
        raise FinalizeError("Prepare manifest must include a paths object.")

    if mode == "markdown":
        return _finalize_markdown(manifest, aggregate_path)
    if mode == "docx_report":
        return _finalize_docx_report(manifest, paths, aggregate_path)

    raise FinalizeError("Prepare manifest mode must be markdown or docx_report.")


def _finalize_markdown(manifest: dict[str, Any], aggregate_path: Path) -> str:
    source_path = _required_manifest_path(manifest, "source_path")
    md_text = source_path.read_text(encoding="utf-8")
    aggregate_output = AggregateOutput.model_validate_json(aggregate_path.read_text(encoding="utf-8"))
    return render_markdown(md_text, [item.verdict for item in aggregate_output.aggregated])


def _finalize_docx_report(manifest: dict[str, Any], paths: dict[str, Any], aggregate_path: Path) -> dict[str, Any]:
    source_map_path = _required_path(paths, "source_map_json")
    report_path = _required_path(paths, "report_md")
    report_json_path = _required_path(paths, "report_json")
    _guard_outputs([report_path, report_json_path], overwrite=bool(manifest.get("overwrite", False)))

    write_audit_report(source_map_path, aggregate_path, report_path, report_json_path)
    payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    return {
        "mode": "docx_report",
        "report": str(report_path),
        "json": str(report_json_path),
        "summary": payload.get("summary"),
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FinalizeError("Prepare manifest must be a JSON object.")
    return payload


def _required_manifest_path(manifest: dict[str, Any], key: str) -> Path:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise FinalizeError(f"Prepare manifest is missing {key}.")
    return Path(value)


def _required_path(paths: dict[str, Any], key: str) -> Path:
    value = paths.get(key)
    if not isinstance(value, str) or not value:
        raise FinalizeError(f"Prepare manifest paths.{key} is required for DOCX report finalization.")
    return Path(value)


def _guard_outputs(paths: list[Path], *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        joined = ", ".join(existing)
        raise FinalizeError(f"Output file already exists: {joined}. Rerun with --overwrite to replace it.")
