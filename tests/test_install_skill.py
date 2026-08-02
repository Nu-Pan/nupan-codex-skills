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
from install_skill import install_all_skills, install_skill  # noqa: E402


class InstallSkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        temporary_root = Path(self.temporary_directory.name)
        self.source_repository = temporary_root / "source"
        self.target_repository = temporary_root / "target"
        self.target_repository.mkdir()

        self.skill_name = "sample-skill"
        self.distribution_root = self._create_distribution(self.skill_name)

    def _create_distribution(self, skill_name: str) -> Path:
        distribution_root = (
            self.source_repository / "skills" / skill_name / "dist"
        )
        (distribution_root / "agents").mkdir(parents=True)
        (distribution_root / "references").mkdir()
        (distribution_root / "SKILL.md").write_text(
            f"---\nname: {skill_name}\n---\n",
            encoding="utf-8",
        )
        (distribution_root / "agents" / "openai.yaml").write_text(
            f'interface:\n  display_name: "{skill_name}"\n',
            encoding="utf-8",
        )
        (distribution_root / "references" / "guide.md").write_text(
            f"{skill_name} guide\n",
            encoding="utf-8",
        )
        return distribution_root

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

    def test_install_all_skills_installs_every_distribution_in_name_order(
        self,
    ) -> None:
        another_skill = "another-skill"
        self._create_distribution(another_skill)
        local_skill = (
            self.target_repository / ".agents" / "skills" / "local-skill"
        )
        local_skill.mkdir(parents=True)
        (local_skill / "SKILL.md").write_text(
            "target-only skill\n",
            encoding="utf-8",
        )

        destinations = install_all_skills(
            self.source_repository,
            self.target_repository,
        )

        expected_names = [another_skill, self.skill_name]
        self.assertEqual(expected_names, [path.name for path in destinations])
        for skill_name, destination in zip(expected_names, destinations, strict=True):
            source_root = self.source_repository / "skills" / skill_name / "dist"
            source_files = {
                path.relative_to(source_root)
                for path in source_root.rglob("*")
                if path.is_file()
            }
            installed_files = {
                path.relative_to(destination)
                for path in destination.rglob("*")
                if path.is_file()
            }
            self.assertEqual(source_files, installed_files)
        self.assertEqual(
            "target-only skill\n",
            (local_skill / "SKILL.md").read_text(encoding="utf-8"),
        )

    def test_all_skills_are_prevalidated_before_installation(self) -> None:
        invalid_distribution = self._create_distribution("zeta-skill")
        (invalid_distribution / "agents" / "openai.yaml").unlink()
        destination = (
            self.target_repository / ".agents" / "skills" / self.skill_name
        )
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_text(
            "previous installation\n",
            encoding="utf-8",
        )
        (self.distribution_root / "SKILL.md").write_text(
            "new distribution\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(FileNotFoundError, "zeta-skill"):
            install_all_skills(
                self.source_repository,
                self.target_repository,
            )

        self.assertEqual(
            "previous installation\n",
            (destination / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertFalse(
            (
                self.target_repository
                / ".agents"
                / "skills"
                / "zeta-skill"
            ).exists()
        )

    def test_failed_all_install_restores_current_skill_only(self) -> None:
        skill_names = ["alpha-skill", self.skill_name, "zeta-skill"]
        self._create_distribution(skill_names[0])
        self._create_distribution(skill_names[2])
        previous_content: dict[str, str] = {}
        for skill_name in skill_names:
            destination = install_skill(
                self.source_repository,
                skill_name,
                self.target_repository,
            )
            previous_content[skill_name] = (destination / "SKILL.md").read_text(
                encoding="utf-8"
            )
            source_file = (
                self.source_repository
                / "skills"
                / skill_name
                / "dist"
                / "SKILL.md"
            )
            source_file.write_text(
                f"updated {skill_name}\n",
                encoding="utf-8",
            )

        failed_destination = (
            self.target_repository / ".agents" / "skills" / self.skill_name
        )
        real_replace = os.replace

        def fail_for_sample_skill(
            source: os.PathLike[str],
            target: os.PathLike[str],
        ) -> None:
            if (
                Path(source).name == "distribution"
                and Path(target) == failed_destination
            ):
                raise OSError("simulated batch failure")
            real_replace(source, target)

        with patch("install_skill.os.replace", side_effect=fail_for_sample_skill):
            with self.assertRaisesRegex(RuntimeError, self.skill_name):
                install_all_skills(
                    self.source_repository,
                    self.target_repository,
                )

        installation_root = self.target_repository / ".agents" / "skills"
        self.assertEqual(
            "updated alpha-skill\n",
            (installation_root / "alpha-skill" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )
        for skill_name in (self.skill_name, "zeta-skill"):
            self.assertEqual(
                previous_content[skill_name],
                (installation_root / skill_name / "SKILL.md").read_text(
                    encoding="utf-8"
                ),
            )
        self.assertEqual([], list(installation_root.glob(".*-install-*")))

    def test_install_all_skills_rejects_missing_or_empty_skills_root(self) -> None:
        for case_name, create_skills_root in (("missing", False), ("empty", True)):
            with self.subTest(case_name=case_name):
                source_repository = (
                    Path(self.temporary_directory.name) / f"source-{case_name}"
                )
                if create_skills_root:
                    (source_repository / "skills").mkdir(parents=True)

                with self.assertRaises(FileNotFoundError):
                    install_all_skills(
                        source_repository,
                        self.target_repository,
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

    def test_main_reports_every_successful_all_installation(self) -> None:
        another_skill = "another-skill"
        self._create_distribution(another_skill)
        standard_output = io.StringIO()
        arguments = [
            "install_skill.py",
            "all",
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

        output = standard_output.getvalue()
        self.assertEqual(0, exit_code)
        self.assertLess(output.index(another_skill), output.index(self.skill_name))
        self.assertIn("全スキルをインストールしました（2 スキル）。", output)


if __name__ == "__main__":
    unittest.main()
