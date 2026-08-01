from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import install_skill as install_skill_module  # noqa: E402
from install_skill import install_skill  # noqa: E402


class InstallSkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        temporary_root = Path(self.temporary_directory.name)
        self.source_repository = temporary_root / "source"
        self.target_repository = temporary_root / "target"
        self.target_repository.mkdir()

        self.skill_name = "sample-skill"
        self.distribution_root = (
            self.source_repository
            / "skills"
            / self.skill_name
            / "dist"
            / self.skill_name
        )
        (self.distribution_root / "agents").mkdir(parents=True)
        (self.distribution_root / "references").mkdir()
        (self.distribution_root / "SKILL.md").write_text(
            "---\nname: sample-skill\n---\n",
            encoding="utf-8",
        )
        (self.distribution_root / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Sample Skill"\n',
            encoding="utf-8",
        )
        (self.distribution_root / "references" / "guide.md").write_text(
            "sample guide\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_install_skill_copies_complete_distribution(self) -> None:
        relative_target = Path(os.path.relpath(self.target_repository, Path.cwd()))
        destination = install_skill(
            self.source_repository,
            self.skill_name,
            relative_target,
        )

        self.assertEqual(
            self.target_repository / ".agents" / "skills" / self.skill_name,
            destination,
        )
        source_files = {
            path.relative_to(self.distribution_root)
            for path in self.distribution_root.rglob("*")
            if path.is_file()
        }
        installed_files = {
            path.relative_to(destination)
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(source_files, installed_files)
        for relative_path in source_files:
            self.assertEqual(
                (self.distribution_root / relative_path).read_bytes(),
                (destination / relative_path).read_bytes(),
            )

    def test_reinstall_replaces_complete_distribution(self) -> None:
        destination = install_skill(
            self.source_repository,
            self.skill_name,
            self.target_repository,
        )
        (destination / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
        (destination / "SKILL.md").write_text("local change\n", encoding="utf-8")
        (self.distribution_root / "SKILL.md").write_text(
            "updated distribution\n",
            encoding="utf-8",
        )

        installed_path = install_skill(
            self.source_repository,
            self.skill_name,
            self.target_repository,
        )

        self.assertEqual(destination, installed_path)
        self.assertEqual(
            "updated distribution\n",
            (installed_path / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((installed_path / "obsolete.txt").exists())
        self.assertEqual(
            [],
            list(
                installed_path.parent.glob(f".{self.skill_name}-install-*")
            ),
        )

    def test_failed_replacement_restores_previous_installation(self) -> None:
        destination = install_skill(
            self.source_repository,
            self.skill_name,
            self.target_repository,
        )
        previous_content = (destination / "SKILL.md").read_text(encoding="utf-8")
        (self.distribution_root / "SKILL.md").write_text(
            "updated distribution\n",
            encoding="utf-8",
        )
        real_replace = os.replace

        def fail_when_promoting(
            source: os.PathLike[str],
            target: os.PathLike[str],
        ) -> None:
            if Path(source).name == "distribution" and Path(target) == destination:
                raise OSError("simulated promotion failure")
            real_replace(source, target)

        with patch("install_skill.os.replace", side_effect=fail_when_promoting):
            with self.assertRaisesRegex(OSError, "simulated promotion failure"):
                install_skill(
                    self.source_repository,
                    self.skill_name,
                    self.target_repository,
                )

        self.assertEqual(
            previous_content,
            (destination / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            [],
            list(destination.parent.glob(f".{self.skill_name}-install-*")),
        )

    def test_invalid_inputs_are_rejected_without_creating_installation(self) -> None:
        missing_target = self.target_repository.parent / "missing-target"
        file_target = self.target_repository.parent / "target-file"
        file_target.write_text("not a directory\n", encoding="utf-8")

        invalid_cases = (
            ("Invalid", self.target_repository, ValueError),
            ("missing-skill", self.target_repository, FileNotFoundError),
            (self.skill_name, missing_target, FileNotFoundError),
            (self.skill_name, file_target, NotADirectoryError),
        )
        for skill_name, target, expected_error in invalid_cases:
            with self.subTest(skill_name=skill_name, target=target):
                with self.assertRaises(expected_error):
                    install_skill(self.source_repository, skill_name, target)

        self.assertFalse((self.target_repository / ".agents").exists())

    def test_missing_required_distribution_file_is_rejected(self) -> None:
        (self.distribution_root / "agents" / "openai.yaml").unlink()

        with self.assertRaisesRegex(FileNotFoundError, "必須ファイル"):
            install_skill(
                self.source_repository,
                self.skill_name,
                self.target_repository,
            )

        self.assertFalse((self.target_repository / ".agents").exists())

    def test_main_reports_successful_installation(self) -> None:
        standard_output = io.StringIO()
        arguments = [
            "install_skill.py",
            self.skill_name,
            str(self.target_repository),
        ]

        with (
            patch.object(
                install_skill_module,
                "REPOSITORY_ROOT",
                self.source_repository,
            ),
            patch.object(sys, "argv", arguments),
            redirect_stdout(standard_output),
        ):
            exit_code = install_skill_module.main()

        destination = (
            self.target_repository / ".agents" / "skills" / self.skill_name
        )
        self.assertEqual(0, exit_code)
        self.assertIn(str(destination), standard_output.getvalue())
        self.assertTrue((destination / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
