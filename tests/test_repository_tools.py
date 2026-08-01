from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from create_skill import create_skill  # noqa: E402
from skill_repository import skill_name_error, validate_repository  # noqa: E402


class RepositoryToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repository_root = Path(self.temporary_directory.name)
        (self.repository_root / "README.md").write_text(
            "# Test skills\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_create_skill_generates_expected_structure(self) -> None:
        skill_root = create_skill(self.repository_root, "sample-skill")

        expected_files = {
            skill_root / "README.md",
            skill_root / "SPEC.md",
            skill_root / "dist" / "SKILL.md",
            skill_root / "dist" / "agents" / "openai.yaml",
        }
        self.assertTrue(all(path.is_file() for path in expected_files))
        self.assertFalse((skill_root / "dist" / "sample-skill").exists())
        self.assertFalse((skill_root / "AGENTS.md").exists())

        readme = (skill_root / "README.md").read_text(encoding="utf-8")
        self.assertIn("[`SPEC.md`](SPEC.md)", readme)
        self.assertIn("[`dist`](dist)", readme)
        self.assertNotIn("../../README.md#インストール", readme)
        self.assertNotIn("## インストール", readme)
        self.assertNotIn("## 呼び出し例", readme)
        self.assertNotIn("$sample-skill", readme)
        self.assertNotIn(".agents/skills/sample-skill", readme)

    def test_create_skill_refuses_invalid_name_and_existing_path(self) -> None:
        for invalid_name in ("Uppercase", "two--hyphens", "ends-", "has space"):
            with self.subTest(invalid_name=invalid_name):
                self.assertIsNotNone(skill_name_error(invalid_name))
                with self.assertRaises(ValueError):
                    create_skill(self.repository_root, invalid_name)

        create_skill(self.repository_root, "sample-skill")
        with self.assertRaises(FileExistsError):
            create_skill(self.repository_root, "sample-skill")

    def test_generated_scaffold_fails_until_completed(self) -> None:
        create_skill(self.repository_root, "sample-skill")

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("{{TODO" in message for message in messages))
        self.assertTrue(any("収録スキル一覧" in message for message in messages))

    def test_completed_skill_passes_validation(self) -> None:
        self._create_completed_skill()

        names, issues = validate_repository(self.repository_root)

        self.assertEqual(["sample-skill"], names)
        self.assertEqual([], issues)

    def test_skill_readme_does_not_require_usage_information(self) -> None:
        skill_root = self._create_completed_skill()

        readme = (skill_root / "README.md").read_text(encoding="utf-8")
        _, issues = validate_repository(self.repository_root)

        self.assertNotIn(".agents/skills/sample-skill", readme)
        self.assertNotIn("$sample-skill", readme)
        self.assertEqual([], issues)

    def test_missing_skill_readme_references_are_reported(self) -> None:
        skill_root = self._create_completed_skill()
        (skill_root / "README.md").write_text(
            "# sample-skill\n\n反復可能なサンプル処理を実行します。\n",
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertIn("仕様の正本へのリンクを記載してください", messages)
        self.assertIn("配布物へのパスを記載してください", messages)

    def test_skill_readme_explicit_invocation_is_reported(self) -> None:
        skill_root = self._create_completed_skill()
        readme = skill_root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\n`$sample-skill` を指定して呼び出します。\n",
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertIn(
            "明示的な呼び出し方法はルート README だけに記載してください",
            messages,
        )

    def test_missing_root_readme_common_usage_is_reported(self) -> None:
        self._create_completed_skill()
        (self.repository_root / "README.md").write_text(
            "# Test skills\n\n"
            "- [sample-skill](skills/sample-skill/README.md)\n",
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("共通インストール手順" in message for message in messages))
        self.assertIn("共通インストール先を記載してください", messages)
        self.assertIn("スキルに共通する呼び出し方法を記載してください", messages)

    def test_manual_install_commands_do_not_satisfy_root_readme(self) -> None:
        self._create_completed_skill()
        (self.repository_root / "README.md").write_text(
            "# Test skills\n\n"
            "- [sample-skill](skills/sample-skill/README.md)\n\n"
            "## インストール\n\n"
            "```bash\n"
            "SKILL_NAME=sample-skill\n"
            "TARGET_REPO=/absolute/path/to/repository\n"
            "mkdir -p \"$TARGET_REPO/.agents/skills/$SKILL_NAME\"\n"
            "```\n\n"
            "## 使用方法\n\n"
            "`$<skill-name>` を指定します。\n",
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertIn(
            "共通インストール手順に正規のスクリプト呼び出しを記載してください",
            messages,
        )
        self.assertIn("共通インストール先を記載してください", messages)

    def test_missing_file_and_mismatched_name_are_reported(self) -> None:
        skill_root = self._create_completed_skill()
        (skill_root / "SPEC.md").unlink()
        skill_file = skill_root / "dist" / "SKILL.md"
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8").replace(
                "name: sample-skill", "name: another-skill"
            ),
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertIn("必須ファイルがありません", messages)
        self.assertTrue(any("name を sample-skill" in message for message in messages))

    def test_forbidden_distribution_file_is_reported(self) -> None:
        skill_root = self._create_completed_skill()
        forbidden_file = skill_root / "dist" / "README.md"
        forbidden_file.write_text("not distributable\n", encoding="utf-8")

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(any("保守用ファイル" in issue.message for issue in issues))

    def test_legacy_distribution_directory_is_reported(self) -> None:
        skill_root = self._create_completed_skill()
        legacy_distribution_root = skill_root / "dist" / "sample-skill"
        legacy_distribution_root.mkdir()

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(
            any("同名の配布用ディレクトリ" in issue.message for issue in issues)
        )

    def test_invalid_openai_metadata_is_reported(self) -> None:
        skill_root = self._create_completed_skill()
        openai_file = skill_root / "dist" / "agents" / "openai.yaml"
        openai_file.write_text(
            '''interface:
  display_name: "Sample Skill"
  short_description: "Too short"
  default_prompt: "Run this task."
''',
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("short_description" in message for message in messages))
        self.assertTrue(any("$sample-skill" in message for message in messages))

    def test_empty_required_metadata_is_reported(self) -> None:
        skill_root = self._create_completed_skill()
        distribution_root = skill_root / "dist"
        skill_file = distribution_root / "SKILL.md"
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8").replace(
                "name: sample-skill", "name:"
            ),
            encoding="utf-8",
        )
        (distribution_root / "agents" / "openai.yaml").write_text(
            '''interface:
  display_name: ""
  short_description: ""
  default_prompt: ""
''',
            encoding="utf-8",
        )

        _, issues = validate_repository(self.repository_root)

        messages = [issue.message for issue in issues]
        self.assertIn("name を空にできません", messages)
        self.assertIn("interface.display_name を空にできません", messages)
        self.assertTrue(any("short_description" in message for message in messages))
        self.assertTrue(any("$sample-skill" in message for message in messages))

    def test_unexpected_entry_under_skills_is_reported(self) -> None:
        self._create_completed_skill()
        (self.repository_root / "skills" / "notes.txt").write_text(
            "unexpected\n", encoding="utf-8"
        )

        _, issues = validate_repository(self.repository_root)

        self.assertTrue(any("skills 直下" in issue.message for issue in issues))

    def _create_completed_skill(self) -> Path:
        skill_name = "sample-skill"
        skill_root = create_skill(self.repository_root, skill_name)
        (self.repository_root / "README.md").write_text(
            "# Test skills\n\n"
            "- [sample-skill](skills/sample-skill/README.md)\n\n"
            "## インストール\n\n"
            "```bash\n"
            "python3 scripts/install_skill.py <skill-name> <target-repository>\n"
            "```\n\n"
            "`<target-repository>/.agents/skills/<skill-name>` へ配置します。\n\n"
            "## 使用方法\n\n"
            "`$<skill-name>` を指定します。\n",
            encoding="utf-8",
        )
        (skill_root / "SPEC.md").write_text(
            "# sample-skill の仕様\n\n"
            "## 目的\n\n"
            "反復可能なサンプル処理を定義する。\n",
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
        return skill_root


if __name__ == "__main__":
    unittest.main()
