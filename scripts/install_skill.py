#!/usr/bin/env python3
"""Install repository skills into an existing target directory."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from skill_repository import ALL_SKILLS_SELECTOR, skill_name_error


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DISTRIBUTION_FILES = (
    Path("SKILL.md"),
    Path("agents") / "openai.yaml",
)


def install_skill(
    repository_root: Path,
    skill_name: str,
    target_repository: Path,
) -> Path:
    """Install one skill and return its final installation path."""

    repository_root = repository_root.resolve()
    distribution_root = _validated_distribution_root(repository_root, skill_name)
    target_repository = _validated_target_repository(target_repository)
    return _install_distribution(distribution_root, skill_name, target_repository)


def install_all_skills(
    repository_root: Path,
    target_repository: Path,
) -> list[Path]:
    """Install every repository skill and return their installation paths."""

    repository_root = repository_root.resolve()
    skill_names = _repository_skill_names(repository_root)
    target_repository = _validated_target_repository(target_repository)
    distributions = [
        (skill_name, _validated_distribution_root(repository_root, skill_name))
        for skill_name in skill_names
    ]

    destinations: list[Path] = []
    for skill_name, distribution_root in distributions:
        try:
            destination = _install_distribution(
                distribution_root,
                skill_name,
                target_repository,
            )
        except (OSError, RuntimeError) as error:
            raise RuntimeError(
                f"{skill_name} のインストールに失敗しました: {error}"
            ) from error
        destinations.append(destination)

    return destinations


def _repository_skill_names(repository_root: Path) -> list[str]:
    skills_root = repository_root / "skills"
    if not skills_root.is_dir():
        raise FileNotFoundError(f"skills ディレクトリがありません: {skills_root}")

    skill_names: list[str] = []
    for entry in sorted(skills_root.iterdir(), key=lambda path: path.name):
        if not entry.is_dir():
            raise ValueError(
                f"skills 直下にはスキルディレクトリだけを置いてください: {entry}"
            )
        skill_names.append(entry.name)

    if not skill_names:
        raise FileNotFoundError(
            f"インストール対象のスキルがありません: {skills_root}"
        )
    return skill_names


def _validated_distribution_root(
    repository_root: Path,
    skill_name: str,
) -> Path:
    name_error = skill_name_error(skill_name)
    if name_error:
        raise ValueError(name_error)

    distribution_root = repository_root / "skills" / skill_name / "dist"
    if not distribution_root.is_dir():
        raise FileNotFoundError(f"スキルの配布物がありません: {distribution_root}")

    for relative_path in REQUIRED_DISTRIBUTION_FILES:
        required_file = distribution_root / relative_path
        if not required_file.is_file():
            raise FileNotFoundError(f"配布物の必須ファイルがありません: {required_file}")

    return distribution_root


def _validated_target_repository(target_repository: Path) -> Path:
    if not target_repository.exists():
        raise FileNotFoundError(
            f"導入先ディレクトリがありません: {target_repository}"
        )
    if not target_repository.is_dir():
        raise NotADirectoryError(
            f"導入先はディレクトリとして指定してください: {target_repository}"
        )
    return target_repository.resolve()


def _install_distribution(
    distribution_root: Path,
    skill_name: str,
    target_repository: Path,
) -> Path:
    installation_root = target_repository / ".agents" / "skills"
    installation_root.mkdir(parents=True, exist_ok=True)
    destination = installation_root / skill_name

    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{skill_name}-install-", dir=installation_root)
    )
    staged_distribution = temporary_root / "distribution"
    previous_installation = temporary_root / "previous"
    preserve_temporary_root = False

    try:
        shutil.copytree(distribution_root, staged_distribution, symlinks=True)

        had_previous_installation = destination.exists() or destination.is_symlink()
        if had_previous_installation:
            os.replace(destination, previous_installation)

        try:
            os.replace(staged_distribution, destination)
        except OSError as install_error:
            if had_previous_installation:
                try:
                    os.replace(previous_installation, destination)
                except OSError as restore_error:
                    preserve_temporary_root = True
                    raise RuntimeError(
                        "新しい配布物の配置と既存版の復元に失敗しました。"
                        f"既存版の退避先: {previous_installation}。"
                        f"復元エラー: {restore_error}"
                    ) from install_error
            raise
    finally:
        if not preserve_temporary_root:
            shutil.rmtree(temporary_root, ignore_errors=True)

    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="スキルを既存の導入先ディレクトリへインストールします。"
    )
    parser.add_argument(
        "skill_name",
        help=f"インストールするスキル名、または全スキルを示す {ALL_SKILLS_SELECTOR}",
    )
    parser.add_argument(
        "target_repository",
        type=Path,
        help="スキルをインストールする既存のディレクトリ",
    )
    args = parser.parse_args()

    try:
        if args.skill_name == ALL_SKILLS_SELECTOR:
            destinations = install_all_skills(
                REPOSITORY_ROOT,
                args.target_repository,
            )
        else:
            destination = install_skill(
                REPOSITORY_ROOT,
                args.skill_name,
                args.target_repository,
            )
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"エラー: {error}\n")

    if args.skill_name == ALL_SKILLS_SELECTOR:
        for destination in destinations:
            print(f"スキルをインストールしました: {destination}")
        print(f"全スキルをインストールしました（{len(destinations)} スキル）。")
    else:
        print(f"スキルをインストールしました: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
