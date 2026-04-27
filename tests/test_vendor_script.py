import subprocess
from pathlib import Path


def test_vendor_dry_run_warns_when_v13_target_would_receive_docx_behavior(repo_root: Path, tmp_path: Path) -> None:
    target = _target_with_vendor_stamp(tmp_path, "1.3.0")

    result = _run_vendor(repo_root, target, "--dry-run", "--no-python")

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "current: v1.3.0" in output
    assert "DOCX behavior will be enabled" in output
    assert "--confirm-docx-upgrade" in output
    assert not (target / ".claude" / "commands" / "audit.md").exists()


def test_vendor_apply_blocks_v13_to_v14_without_docx_confirmation(repo_root: Path, tmp_path: Path) -> None:
    target = _target_with_vendor_stamp(tmp_path, "1.3.0")

    result = _run_vendor(repo_root, target, "--no-python")

    assert result.returncode == 2
    output = result.stdout + result.stderr
    assert "target is currently vendored at v1.3.0" in output
    assert "rerun with --confirm-docx-upgrade" in output
    assert not (target / ".claude" / "commands" / "audit.md").exists()


def test_vendor_apply_allows_confirmed_v13_to_v14_docx_upgrade(repo_root: Path, tmp_path: Path) -> None:
    target = _target_with_vendor_stamp(tmp_path, "1.3.0")

    result = _run_vendor(repo_root, target, "--no-python", "--confirm-docx-upgrade")

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "DOCX upgrade confirmation received" in output
    assert (target / ".claude" / "commands" / "audit.md").exists()
    stamp = target / ".claude" / "skills" / "citation-auditor" / "VENDOR.md"
    assert "- Version: **v1.4.0**" in stamp.read_text(encoding="utf-8")


def _run_vendor(repo_root: Path, target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo_root / "scripts" / "vendor-into.sh"), str(target), *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _target_with_vendor_stamp(tmp_path: Path, version: str) -> Path:
    target = tmp_path / "target"
    stamp_dir = target / ".claude" / "skills" / "citation-auditor"
    stamp_dir.mkdir(parents=True)
    (stamp_dir / "VENDOR.md").write_text(
        f"""# citation-auditor vendor stamp

- Version: **v{version}**
- Source commit: old
""",
        encoding="utf-8",
    )
    return target
