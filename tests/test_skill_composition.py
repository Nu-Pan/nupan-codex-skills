from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from create_skill import create_skill  # noqa: E402
from skill_repository import validate_repository  # noqa: E402


class SkillCompositionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repository_root = Path(self.temporary_directory.name)
        self.skill_names = ["alpha-skill", "beta-skill"]
        for skill_name in self.skill_names:
            self._create_completed_skill(skill_name)
        self._write_root_readme()
        self.registry = self._valid_registry()
        self._write_registry()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_valid_orthogonal_registry_passes(self) -> None:
        names, issues = validate_repository(self.repository_root)

        self.assertEqual(self.skill_names, names)
        self.assertEqual([], issues)

    def test_valid_overlap_scenario_passes(self) -> None:
        self.registry["combination_scenarios"] = [
            {
                "id": "combined-change",
                "skills": self.skill_names,
                "request": "Use both skills for one change.",
                "expected": ["Both sets of rules are satisfied."],
                "forbidden": ["One skill silently overrides the other."],
            }
        ]
        self.registry["pairs"][0] = {
            "skills": self.skill_names,
            "relation": "overlap",
            "scenario_ids": ["combined-change"],
        }
        self._write_registry()

        _, issues = validate_repository(self.repository_root)

        self.assertEqual([], issues)

    def test_missing_and_duplicate_registry_data_are_reported(self) -> None:
        (self.repository_root / "skill-composition.json").unlink()

        _, missing_issues = validate_repository(self.repository_root)

        self.assertTrue(any("組み合わせ台帳がありません" in issue.message for issue in missing_issues))

        (self.repository_root / "skill-composition.json").write_text(
            '{"version": 1, "version": 1}\n', encoding="utf-8"
        )
        _, duplicate_issues = validate_repository(self.repository_root)

        self.assertTrue(any("キーが重複" in issue.message for issue in duplicate_issues))

    def test_every_skill_requires_one_standalone_scenario(self) -> None:
        self.registry["standalone_scenarios"].pop()
        self._write_registry()

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(any("単独シナリオがありません: beta-skill" in issue.message for issue in issues))

    def test_every_skill_pair_requires_one_classification(self) -> None:
        self.registry["pairs"] = []
        self._write_registry()

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(
            any("pair がありません: alpha-skill, beta-skill" in issue.message for issue in issues)
        )

    def test_overlap_pair_requires_matching_scenario(self) -> None:
        self.registry["pairs"][0]["relation"] = "overlap"
        self._write_registry()

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(
            any("overlap pair には scenario_ids が必要" in issue.message for issue in issues)
        )

    def test_optional_reference_requires_declaration_and_fallback(self) -> None:
        alpha_spec = self.repository_root / "skills" / "alpha-skill" / "SPEC.md"
        alpha_spec.write_text(
            alpha_spec.read_text(encoding="utf-8")
            + "\n利用可能な場合は $beta-skill の結果を再利用する。\n",
            encoding="utf-8",
        )

        _, undeclared_issues = validate_repository(self.repository_root)

        self.assertTrue(any("台帳にない任意参照" in issue.message for issue in undeclared_issues))

        self.registry["optional_references"] = [
            {
                "source": "alpha-skill",
                "target": "beta-skill",
                "locations": ["SPEC.md"],
                "fallback": "Run the same check locally when beta-skill is absent.",
            }
        ]
        self._write_registry()
        _, valid_issues = validate_repository(self.repository_root)
        self.assertEqual([], valid_issues)

        self.registry["optional_references"][0]["fallback"] = ""
        self._write_registry()
        _, fallback_issues = validate_repository(self.repository_root)
        self.assertTrue(any("fallback は空でない文字列" in issue.message for issue in fallback_issues))

    def test_bare_skill_name_and_direct_path_reference_are_reported(self) -> None:
        alpha_spec = self.repository_root / "skills" / "alpha-skill" / "SPEC.md"
        alpha_spec.write_text(
            alpha_spec.read_text(encoding="utf-8")
            + "\nbeta-skill と skills/beta-skill/SPEC.md を参照する。\n",
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("$ を付けた任意参照" in message for message in messages))
        self.assertTrue(any("別のスキルへの直接パス参照" in message for message in messages))

    def test_dangling_repository_path_reference_is_reported(self) -> None:
        readme = self.repository_root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\n[missing](skills/missing-skill/README.md)\n",
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(any("存在しないスキルへのパス参照" in issue.message for issue in issues))

    def test_only_spec_composition_heading_is_required(self) -> None:
        alpha_skill = self.repository_root / "skills" / "alpha-skill" / "dist" / "SKILL.md"
        self.assertNotIn(
            "## 他のスキルとの合成",
            alpha_skill.read_text(encoding="utf-8"),
        )
        _, valid_issues = validate_repository(self.repository_root)
        self.assertEqual([], valid_issues)

        alpha_spec = self.repository_root / "skills" / "alpha-skill" / "SPEC.md"
        alpha_spec.write_text(
            alpha_spec.read_text(encoding="utf-8").replace(
                "## 独立性と合成", "## Composition"
            ),
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(any("合成規則の見出し" in issue.message for issue in issues))

    def test_targeted_validation_still_checks_complete_registry(self) -> None:
        self.registry["pairs"] = []
        self._write_registry()

        names, issues = validate_repository(self.repository_root, ["alpha-skill"])

        self.assertEqual(["alpha-skill"], names)
        self.assertTrue(any("pair がありません" in issue.message for issue in issues))

    def _create_completed_skill(self, skill_name: str) -> None:
        skill_root = create_skill(self.repository_root, skill_name)
        (skill_root / "SPEC.md").write_text(
            f"# {skill_name} の仕様\n\n"
            "## 目的\n\n"
            "サンプル処理を定義する。\n\n"
            "## 独立性と合成\n\n"
            "単独で処理し、両立する規則を累積する。\n",
            encoding="utf-8",
        )
        (skill_root / "README.md").write_text(
            f"# {skill_name}\n\n"
            "サンプル処理を実行します。\n\n"
            "仕様は [SPEC.md](SPEC.md) にあります。\n"
            "配布物は [dist](dist) にあります。\n",
            encoding="utf-8",
        )
        distribution_root = skill_root / "dist"
        (distribution_root / "SKILL.md").write_text(
            "---\n"
            f"name: {skill_name}\n"
            "description: Run a sample task when composition behavior needs validation.\n"
            "---\n\n"
            "# Run a sample task\n\n"
            "## 実行\n\n"
            "Validate the input and return the result.\n",
            encoding="utf-8",
        )
        (distribution_root / "agents" / "openai.yaml").write_text(
            "interface:\n"
            f'  display_name: "{skill_name}"\n'
            '  short_description: "Run repeatable composition sample tasks"\n'
            f'  default_prompt: "Use ${skill_name} to run this sample task."\n',
            encoding="utf-8",
        )

    def _write_root_readme(self) -> None:
        skill_links = "\n".join(
            f"- [{skill_name}](skills/{skill_name}/README.md)"
            for skill_name in self.skill_names
        )
        (self.repository_root / "README.md").write_text(
            "# Test skills\n\n"
            f"{skill_links}\n\n"
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

    def _valid_registry(self) -> dict[str, object]:
        return {
            "version": 1,
            "optional_references": [],
            "standalone_scenarios": [
                {
                    "id": f"{skill_name}-standalone",
                    "skill": skill_name,
                    "request": f"Run {skill_name} alone.",
                    "expected": ["The task completes."],
                    "forbidden": ["Another skill is required."],
                }
                for skill_name in self.skill_names
            ],
            "combination_scenarios": [],
            "pairs": [
                {
                    "skills": self.skill_names,
                    "relation": "orthogonal",
                    "scenario_ids": [],
                }
            ],
        }

    def _write_registry(self) -> None:
        (self.repository_root / "skill-composition.json").write_text(
            json.dumps(self.registry, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
