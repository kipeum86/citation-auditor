from pathlib import Path


def test_bundled_verifiers_use_metadata_for_routing_fields(repo_root: Path) -> None:
    verifier_paths = sorted((repo_root / "skills" / "verifiers").glob("*/SKILL.md"))

    assert verifier_paths
    for path in verifier_paths:
        frontmatter = _frontmatter(path)
        assert "\nmetadata:\n" in frontmatter
        assert "\n  patterns:\n" in frontmatter
        assert "\n  authority:" in frontmatter
        assert "\npatterns:" not in frontmatter
        assert "\nauthority:" not in frontmatter

    primary_skill = (repo_root / "skills" / "citation-auditor" / "SKILL.md").read_text(encoding="utf-8")
    assert "metadata.patterns" in primary_skill
    assert "metadata.authority" in primary_skill
    assert "top-level frontmatter `patterns`" in primary_skill
    assert "top-level frontmatter `authority`" in primary_skill


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    _, frontmatter, _ = text.split("---", 2)
    return frontmatter
