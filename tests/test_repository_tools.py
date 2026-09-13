from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from create_skill import create_skill
from skill_names import skill_name_error
from skill_repository import validate_repository


@pytest.fixture
def completed_skill(tmp_path: Path) -> Path:
    return create_completed_skill(tmp_path)


def assert_rejected_at(repository: Path, path: Path) -> None:
    issues = validate_repository(repository)[1]
    assert any(issue.path == path and issue.message.strip() for issue in issues)


def test_scaffold_has_required_structure_and_unfinished_placeholders(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Test skills\n", encoding="utf-8")
    root = create_skill(tmp_path, "sample-skill")
    expected = {"README.md", "SPEC.md", "dist/SKILL.md", "dist/agents/openai.yaml"}
    assert all((root / name).is_file() for name in expected)
    assert not (root / "dist/sample-skill").exists()
    assert not (root / "AGENTS.md").exists()
    content = "\n".join((root / name).read_text(encoding="utf-8") for name in expected)
    placeholders = re.findall(r"\{\{([^{}]+)\}\}", content)
    assert placeholders
    assert all(re.fullmatch(r"todo-[a-z0-9]+(?:-[a-z0-9]+)*", name) for name in placeholders)
    issues = validate_repository(tmp_path)[1]
    assert any(issue.path == root / "SPEC.md" for issue in issues)
    assert any(issue.path == tmp_path / "README.md" for issue in issues)
    # Removing unfinished text must leave usable navigation in the scaffold.
    readme = root / "README.md"
    readme.write_text(re.sub(r"\{\{todo-[^{}]+\}\}", "Sample task", readme.read_text()))
    assert not any(issue.path == readme for issue in validate_repository(tmp_path)[1])


@pytest.mark.parametrize("name", ["", "Uppercase", "two--hyphens", "ends-", "has space", "all", "a" * 65])
def test_invalid_skill_name_is_rejected(tmp_path: Path, name: str) -> None:
    assert skill_name_error(name) is not None
    with pytest.raises(ValueError):
        create_skill(tmp_path, name)
    assert not (tmp_path / "skills").exists()


def test_existing_scaffold_is_not_overwritten(tmp_path: Path) -> None:
    root = create_skill(tmp_path, "sample-skill")
    marker = root / "SPEC.md"
    marker.write_text("existing specification\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_skill(tmp_path, "sample-skill")
    assert marker.read_text() == "existing specification\n"


def test_completed_skill_passes_without_duplicating_usage_information(completed_skill: Path) -> None:
    names, issues = validate_repository(completed_skill.parents[1])
    assert names == ["sample-skill"]
    assert issues == []


@pytest.mark.parametrize("content", [
    "# sample-skill\n\nSample task.\n",
    "SPEC.md と (dist)",
    "`[仕様](SPEC.md)` と `[配布](dist)`",
    "```markdown\n[仕様](SPEC.md) と [配布](dist)\n```",
    "[仕様](missing/SPEC.md) と [配布](missing/dist)",
    "[仕様](https://example.com/SPEC.md) と [配布](https://example.com/dist)",
    "[仕様](SPEC.md)",
    "[配布](dist)",
])
def test_skill_readme_requires_both_actual_links(completed_skill: Path, content: str) -> None:
    path = completed_skill / "README.md"
    path.write_text(content, encoding="utf-8")
    assert_rejected_at(completed_skill.parents[1], path)


@pytest.mark.parametrize("content", [
    "[正本](./SPEC.md) と [配布](./dist/)。",
    "[正本][spec] と [配布][dist]。\n\n[spec]: SPEC.md\n[dist]: dist/\n",
    '<a href="SPEC.md">正本</a> と <a href="dist/">配布</a>。',
    "| 正本 | 配布 |\n| --- | --- |\n| [仕様](SPEC.md) | [資源](dist/) |\n",
])
def test_skill_readme_accepts_equivalent_link_targets(completed_skill: Path, content: str) -> None:
    (completed_skill / "README.md").write_text(content, encoding="utf-8")
    assert validate_repository(completed_skill.parents[1])[1] == []


def test_skill_readme_does_not_duplicate_invocation_instructions(completed_skill: Path) -> None:
    path = completed_skill / "README.md"
    path.write_text(path.read_text() + "\n`$sample-skill` を指定して呼び出します。\n")
    assert_rejected_at(completed_skill.parents[1], path)


@pytest.mark.parametrize("fragment", [
    "python3 scripts/install_skill.py {{skill-name}} {{target-repository}}",
    "python3 scripts/install_skill.py all {{target-repository}}",
    ".agents/skills/{{skill-name}}",
    "${{skill-name}}",
])
def test_root_readme_requires_common_usage(completed_skill: Path, fragment: str) -> None:
    path = completed_skill.parents[1] / "README.md"
    path.write_text(path.read_text().replace(fragment, ""))
    assert_rejected_at(completed_skill.parents[1], path)


def test_manual_copy_does_not_replace_install_command(completed_skill: Path) -> None:
    path = completed_skill.parents[1] / "README.md"
    path.write_text(path.read_text().replace(
        "python3 scripts/install_skill.py {{skill-name}} {{target-repository}}",
        'mkdir -p target/.agents/skills/sample-skill\ncp -r skills/sample-skill/dist target/.agents/skills/sample-skill',
    ))
    assert_rejected_at(completed_skill.parents[1], path)


@pytest.mark.parametrize("link,valid", [
    ("[sample](./skills/sample-skill/README.md)", True),
    ("`skills/sample-skill/README.md`", False),
    ("[sample](https://example.com/skills/sample-skill/README.md)", False),
])
def test_root_readme_requires_a_link_to_each_skill(completed_skill: Path, link: str, valid: bool) -> None:
    path = completed_skill.parents[1] / "README.md"
    path.write_text(path.read_text().replace("[sample-skill](skills/sample-skill/README.md)", link))
    issues = validate_repository(completed_skill.parents[1])[1]
    assert (not issues) is valid
    if not valid:
        assert any(issue.path == path for issue in issues)


def test_missing_required_file_is_reported(completed_skill: Path) -> None:
    path = completed_skill / "SPEC.md"
    path.unlink()
    assert_rejected_at(completed_skill.parents[1], path)


@pytest.mark.parametrize("description", [
    ">\n  Run repeatable tasks\n  when validation is needed.",
    "|-\n  Run repeatable tasks.\n  Use for validation.",
    '"Run # repeatable tasks." # description comment',
])
def test_frontmatter_uses_yaml_string_values(completed_skill: Path, description: str) -> None:
    (completed_skill / "dist/SKILL.md").write_text(
        "---\nname: sample-skill # name comment\n"
        f"description: {description}\n---\n\nRun the sample task.\n", encoding="utf-8",
    )
    assert validate_repository(completed_skill.parents[1])[1] == []


@pytest.mark.parametrize("metadata", [
    "name: another-skill\ndescription: Sample task.",
    "name:\ndescription: Sample task.",
    "name: sample-skill\ndescription: [sample]",
    "name: true\ndescription: Sample task.",
    "name: sample-skill\ndescription: null",
    "name: sample-skill\nname: another-skill\ndescription: Sample task.",
    "name: sample-skill\ndescription: <table>",
    "name: sample-skill\ndescription: `$sample-skill` runs sample tasks.",
])
def test_invalid_frontmatter_is_reported(completed_skill: Path, metadata: str) -> None:
    path = completed_skill / "dist/SKILL.md"
    path.write_text(f"---\n{metadata}\n---\n\nRun the sample task.\n", encoding="utf-8")
    assert_rejected_at(completed_skill.parents[1], path)


@pytest.mark.parametrize("metadata", [
    'metadata:\n  version: "1.0"\n',
    'license: "MIT"\ncompatibility: "Python 3.12"\n',
])
def test_frontmatter_accepts_additional_metadata(completed_skill: Path, metadata: str) -> None:
    (completed_skill / "dist/SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Sample task.\n"
        + metadata + "---\n\nRun the sample task.\n", encoding="utf-8",
    )
    assert validate_repository(completed_skill.parents[1])[1] == []


@pytest.mark.parametrize("name", ["README.md", "SPEC.md", "AGENTS.md", "LICENSE"])
def test_maintenance_files_are_not_distributed(completed_skill: Path, name: str) -> None:
    path = completed_skill / "dist" / name
    path.write_text("not distributable\n", encoding="utf-8")
    assert_rejected_at(completed_skill.parents[1], path)


def test_distribution_is_not_nested_under_its_skill_name(completed_skill: Path) -> None:
    path = completed_skill / "dist/sample-skill"
    path.mkdir()
    assert_rejected_at(completed_skill.parents[1], path)


@pytest.mark.parametrize("content", [
    '''interface: # display
    display_name: 'Reader''s Skill'
    short_description: "Run repeatable repository sample tasks" # help
    default_prompt: "Use $sample-skill to run this sample task."
policy:
    allow_implicit_invocation: false
''',
    'interface: {display_name: "Sample Skill", short_description: "Run repeatable repository sample tasks", default_prompt: "Use $sample-skill to run this sample task."}\n',
])
def test_openai_metadata_uses_yaml_values(completed_skill: Path, content: str) -> None:
    (completed_skill / "dist/agents/openai.yaml").write_text(content, encoding="utf-8")
    assert validate_repository(completed_skill.parents[1])[1] == []


@pytest.mark.parametrize("old,new", [
    ('display_name: "Sample Skill"', 'display_name: "Sample Skill"broken"'),
    ('display_name: "Sample Skill"', 'display_name: "First"\n  display_name: "Second"'),
    ('display_name: "Sample Skill"', 'display_name: Sample Skill'),
    ('display_name: "Sample Skill"', 'display_name: ["Sample Skill"]'),
    ('display_name: "Sample Skill"', 'display_name: ""'),
    ('interface:', 'interface: []\ninvalid:'),
    ('  display_name: "Sample Skill"', '  1: "Sample Skill"'),
    ('short_description: "Run repeatable repository sample tasks"', 'short_description: "Too short"'),
    ('short_description: "Run repeatable repository sample tasks"', 'short_description: ""'),
    ('default_prompt: "Use $sample-skill to run this sample task."', 'default_prompt: "Run the task."'),
    ('default_prompt: "Use $sample-skill to run this sample task."', 'default_prompt: ""'),
])
def test_openai_metadata_rejects_invalid_structure_and_values(
    completed_skill: Path, old: str, new: str
) -> None:
    path = completed_skill / "dist/agents/openai.yaml"
    path.write_text(path.read_text().replace(old, new), encoding="utf-8")
    assert_rejected_at(completed_skill.parents[1], path)


def test_skills_directory_contains_only_skills(completed_skill: Path) -> None:
    path = completed_skill.parent / "notes.txt"
    path.write_text("unexpected\n", encoding="utf-8")
    assert_rejected_at(completed_skill.parents[1], path)


def create_completed_skill(repository_root: Path) -> Path:
    skill_name = "sample-skill"
    skill_root = create_skill(repository_root, skill_name)
    (repository_root / "README.md").write_text(
        "# Test skills\n\n"
        "- [sample-skill](skills/sample-skill/README.md)\n\n"
        "## インストール\n\n"
        "```bash\n"
        "python3 scripts/install_skill.py {{skill-name}} {{target-repository}}\n"
        "python3 scripts/install_skill.py all {{target-repository}}\n"
        "```\n\n"
        "`{{target-repository}}/.agents/skills/{{skill-name}}` へ配置します。\n\n"
        "## 使用方法\n\n"
        "`${{skill-name}}` を指定します。\n",
        encoding="utf-8",
    )
    (skill_root / "SPEC.md").write_text(
        "# sample-skill の仕様\n\n"
        "## 目的\n\n"
        "反復可能なサンプル処理を定義する。\n"
        "単独で処理し、他の規則と両立させる。\n",
        encoding="utf-8",
    )
    (skill_root / "README.md").write_text(
        "# sample-skill\n\n"
        "反復可能なサンプル処理を実行します。\n\n"
        "仕様は [SPEC.md](SPEC.md) にあります。\n"
        "配布物は [dist](dist) にあります。\n",
        encoding="utf-8",
    )
    distribution_root = skill_root / "dist"
    (distribution_root / "SKILL.md").write_text(
        "---\n"
        "name: sample-skill\n"
        "description: Run repeatable sample tasks when repository behavior needs validation.\n"
        "---\n\n"
        "# Run sample tasks\n\n"
        "## 実行\n\n"
        "Validate the input and return the result.\n",
        encoding="utf-8",
    )
    (distribution_root / "agents" / "openai.yaml").write_text(
        '''interface:
  display_name: "Sample Skill"
  short_description: "Run repeatable repository sample tasks"
  default_prompt: "Use $sample-skill to run this sample task."
''',
        encoding="utf-8",
    )
    (repository_root / "skill-composition.json").write_text(
        json.dumps(
            {
                "version": 2,
                "optional_references": [],
                "standalone_scenarios": [
                    {
                        "id": "sample-skill-standalone",
                        "skill": "sample-skill",
                        "request": "Run a repeatable sample task.",
                        "expected": ["The task completes."],
                        "forbidden": ["Another skill is required."],
                    }
                ],
                "combination_scenarios": [],
                "pairs": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return skill_root
