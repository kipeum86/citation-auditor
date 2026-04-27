from pathlib import Path


def test_local_only_flags_are_explicit_in_command_and_primary_skill(repo_root: Path) -> None:
    command = (repo_root / "commands" / "audit.md").read_text(encoding="utf-8")
    skill = (repo_root / "skills" / "citation-auditor" / "SKILL.md").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    for flag in ("--local-only", "--no-web", "--offline"):
        assert flag in command
        assert flag in skill
        assert flag in readme

    assert "--overwrite" in command
    assert "--overwrite" in skill
    assert "python -m citation_auditor prepare" in skill
    assert "paths.aggregate_input_json" in skill
    assert "paths.report_md" in skill
    assert "Pass `$ARGUMENTS` through unchanged" in command
    assert "Parse `$ARGUMENTS` into optional flags and one file path" in skill
    assert "Do not infer `local_only` from natural-language sensitivity words alone" in skill
    assert '"local_only": <local_only>' in skill
