from __future__ import annotations

import json
from pathlib import Path

import pytest


from create_skill import create_skill
from skill_repository import validate_repository


SKILLS = ["alpha-skill", "beta-skill"]


@pytest.fixture
def registry():
    return {
        "version": 2,
        "optional_references": [],
        "standalone_scenarios": [
            {
                "id": f"{name}-standalone",
                "skill": name,
                "request": f"Run {name} alone.",
                "expected": ["The task completes."],
                "forbidden": ["Another skill is required."],
            }
            for name in SKILLS
        ],
        "combination_scenarios": [],
        "pairs": [{"skills": SKILLS.copy(), "relation": "orthogonal", "scenario_ids": []}],
    }


def write_registry(repository: Path, registry) -> None:
    (repository / "skill-composition.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


@pytest.fixture
def repository(tmp_path: Path, registry) -> Path:
    for name in SKILLS:
        root = create_skill(tmp_path, name)
        (root / "SPEC.md").write_text(f"# {name}\n\nサンプル処理を定義する。\n")
        (root / "README.md").write_text(
            f"# {name}\n\n仕様は [SPEC.md](SPEC.md)、配布物は [dist](dist)。\n"
        )
        (root / "dist" / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Run a sample composition task.\n---\n\n"
            "Validate the input and return the result.\n"
        )
        (root / "dist" / "agents" / "openai.yaml").write_text(
            "interface:\n"
            f'  display_name: "{name}"\n'
            '  short_description: "Run repeatable composition sample tasks"\n'
            f'  default_prompt: "Use ${name} to run this sample task."\n'
        )
    links = "\n".join(f"- [{name}](skills/{name}/README.md)" for name in SKILLS)
    (tmp_path / "README.md").write_text(
        f"# Test skills\n\n{links}\n\n"
        "```bash\n"
        "python3 scripts/install_skill.py {{skill-name}} {{target-repository}}\n"
        "python3 scripts/install_skill.py all {{target-repository}}\n"
        "```\n\n"
        "`{{target-repository}}/.agents/skills/{{skill-name}}` へ配置します。\n"
        "`${{skill-name}}` を指定します。\n"
    )
    write_registry(tmp_path, registry)
    return tmp_path


@pytest.fixture
def scenario():
    return {
        "id": "combined-change",
        "skills": SKILLS.copy(),
        "applicable_skills": SKILLS.copy(),
        "request": "Complete the requested task.",
        "expected": ["Applicable rules are satisfied and shared work is reused."],
        "forbidden": ["Installed skills add unrelated work."],
    }


def messages(repository: Path, registry) -> list[str]:
    write_registry(repository, registry)
    return [issue.message for issue in validate_repository(repository)[1]]


def test_valid_orthogonal_registry_passes(repository: Path) -> None:
    names, issues = validate_repository(repository)
    assert names == SKILLS
    assert issues == []


def test_valid_overlap_scenario_passes(repository: Path, registry, scenario) -> None:
    registry["combination_scenarios"] = [scenario]
    registry["pairs"][0].update(relation="overlap", scenario_ids=[scenario["id"]])
    assert messages(repository, registry) == []


@pytest.mark.parametrize("applicable", [[], ["alpha-skill"], SKILLS])
def test_unreferenced_application_scenario_passes(
    repository: Path, registry, scenario, applicable
) -> None:
    scenario["applicable_skills"] = applicable
    registry["combination_scenarios"] = [scenario]
    assert messages(repository, registry) == []


@pytest.mark.parametrize(
    ("applicable", "fragment"),
    [
        (None, "applicable_skills は"),
        ([{}], "applicable_skills は"),
        (["alpha-skill", "alpha-skill"], "applicable_skills に重複"),
        (list(reversed(SKILLS)), "applicable_skills を名前順"),
        (["missing-skill"], "導入対象にないスキル"),
    ],
)
def test_invalid_applicable_skills_are_reported(
    repository: Path, registry, scenario, applicable, fragment: str
) -> None:
    scenario["applicable_skills"] = applicable
    registry["combination_scenarios"] = [scenario]
    registry["pairs"][0].update(relation="overlap", scenario_ids=[scenario["id"]])
    assert any(fragment in message for message in messages(repository, registry))


def test_applicable_skill_must_be_installed_even_when_known(
    repository: Path, registry, scenario
) -> None:
    registry["combination_scenarios"] = [scenario]
    scenario["skills"] = ["alpha-skill", "missing-skill"]
    assert any(
        "導入対象にないスキル" in m and "beta-skill" in m
        for m in messages(repository, registry)
    )


def test_applicable_skills_is_required(repository: Path, registry, scenario) -> None:
    del scenario["applicable_skills"]
    registry["combination_scenarios"] = [scenario]
    assert any("applicable_skills がありません" in m for m in messages(repository, registry))


@pytest.mark.parametrize("applicable", [[], ["alpha-skill"]])
def test_installed_but_inapplicable_skill_does_not_prove_overlap(
    repository: Path, registry, scenario, applicable
) -> None:
    registry["combination_scenarios"] = [scenario]
    scenario["applicable_skills"] = applicable
    registry["pairs"][0].update(relation="overlap", scenario_ids=[scenario["id"]])
    assert any("applicable_skills に pair の両スキルがありません" in m for m in messages(repository, registry))


def test_missing_and_duplicate_registry_data_are_reported(repository: Path) -> None:
    path = repository / "skill-composition.json"
    path.unlink()
    assert any("組み合わせ台帳がありません" in i.message for i in validate_repository(repository)[1])
    path.write_text('{"version": 2, "version": 2}\n')
    assert any("キーが重複" in i.message for i in validate_repository(repository)[1])


def test_every_skill_requires_one_standalone_scenario(repository: Path, registry) -> None:
    registry["standalone_scenarios"].pop()
    assert any("単独シナリオがありません: beta-skill" in m for m in messages(repository, registry))


@pytest.mark.parametrize("version", [True, 2.0, "2", 1, 3])
def test_version_requires_integer_two(repository: Path, registry, version) -> None:
    registry["version"] = version
    assert any("version は整数の 2" in m for m in messages(repository, registry))


def test_every_skill_pair_requires_one_classification(repository: Path, registry) -> None:
    registry["pairs"] = []
    assert any("pair がありません: alpha-skill, beta-skill" in m for m in messages(repository, registry))


def test_overlap_pair_requires_matching_scenario(repository: Path, registry) -> None:
    registry["pairs"][0]["relation"] = "overlap"
    assert any("overlap pair には scenario_ids が必要" in m for m in messages(repository, registry))


@pytest.mark.parametrize("reference", ["$beta-skill", "beta-skill"])
def test_optional_reference_requires_declaration_and_fallback(
    repository: Path, registry, reference: str
) -> None:
    path = repository / "skills" / "alpha-skill" / "SPEC.md"
    path.write_text(path.read_text() + f"\n利用可能な場合は {reference} の結果を再利用する。\n")
    assert any("台帳にない任意参照" in m for m in messages(repository, registry))
    registry["optional_references"] = [{
        "source": "alpha-skill", "target": "beta-skill", "locations": ["SPEC.md"],
        "fallback": "Run the same check locally when beta-skill is absent.",
    }]
    assert messages(repository, registry) == []
    registry["optional_references"][0]["fallback"] = ""
    assert any("fallback は空でない文字列" in m for m in messages(repository, registry))


def test_undeclared_skill_name_and_direct_path_reference_are_reported(
    repository: Path, registry
) -> None:
    path = repository / "skills" / "alpha-skill" / "SPEC.md"
    path.write_text(path.read_text() + "\nbeta-skill と skills/beta-skill/SPEC.md を参照する。\n")
    found = messages(repository, registry)
    assert any("台帳にない任意参照" in m for m in found)
    assert any("別のスキルへの直接パス参照" in m for m in found)


def test_dangling_repository_path_reference_is_reported(repository: Path, registry) -> None:
    path = repository / "README.md"
    path.write_text(path.read_text() + "\n[missing](skills/missing-skill/README.md)\n")
    assert any("存在しないスキルへのパス参照" in m for m in messages(repository, registry))


@pytest.mark.parametrize("content", [
    "# Alpha\n\n## 判断基準\n\n対象の処理を単独で実行する。\n",
    "# Alpha\n\n対象の処理を実行する。他の処理とは結果を共用できる。\n",
])
def test_spec_layout_does_not_determine_composition_validity(
    repository: Path, registry, content: str
) -> None:
    (repository / "skills" / "alpha-skill" / "SPEC.md").write_text(content)
    assert messages(repository, registry) == []
    registry["pairs"] = []
    assert any("pair がありません" in m for m in messages(repository, registry))


def test_targeted_validation_still_checks_complete_registry(repository: Path, registry) -> None:
    registry["pairs"] = []
    write_registry(repository, registry)
    names, issues = validate_repository(repository, ["alpha-skill"])
    assert names == ["alpha-skill"]
    assert any("pair がありません" in i.message for i in issues)


@pytest.mark.parametrize("invalid", [None, False, 7, [], {}])
@pytest.mark.parametrize("field", ["skill", "relation"])
def test_invalid_identifier_types_are_diagnosed_without_crashing(
    repository: Path, registry, invalid, field: str
) -> None:
    if field == "skill":
        registry["standalone_scenarios"][0][field] = invalid
    else:
        registry["pairs"][0][field] = invalid

    found = messages(repository, registry)

    assert any(field in message for message in found)
