from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import install_skill as installer
from install_skill import install_all_skills, install_skill


@pytest.fixture
def source_repository(tmp_path: Path) -> Path:
    return tmp_path / "source"


@pytest.fixture
def target_repository(tmp_path: Path) -> Path:
    target = tmp_path / "target"
    target.mkdir()
    return target


@pytest.fixture
def distribution(source_repository: Path) -> Path:
    return create_distribution(source_repository, "sample-skill")


def create_distribution(repository: Path, name: str) -> Path:
    root = repository / "skills" / name / "dist"
    (root / "agents").mkdir(parents=True)
    (root / "references").mkdir()
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Run sample tasks.\n---\n\nRun the task.\n",
        encoding="utf-8",
    )
    (root / "agents/openai.yaml").write_text(
        f'interface:\n  display_name: "{name}"\n'
        '  short_description: "Run repeatable sample repository tasks"\n'
        f'  default_prompt: "Use ${name} to run the task."\n', encoding="utf-8",
    )
    (root / "references/guide.md").write_text(f"{name} guide\n", encoding="utf-8")
    return root


def contents(root: Path) -> dict[Path, bytes]:
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("relative", [False, True])
def test_install_copies_complete_distribution(
    source_repository: Path, target_repository: Path, distribution: Path, relative: bool
) -> None:
    target = Path(os.path.relpath(target_repository)) if relative else target_repository
    destination = install_skill(source_repository, "sample-skill", target)
    assert destination == target_repository / ".agents/skills/sample-skill"
    assert contents(destination) == contents(distribution)


def test_reinstall_replaces_complete_distribution(
    source_repository: Path, target_repository: Path, distribution: Path
) -> None:
    destination = install_skill(source_repository, "sample-skill", target_repository)
    (destination / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    (destination / "SKILL.md").write_text("local change\n", encoding="utf-8")
    (distribution / "SKILL.md").write_text("updated distribution\n", encoding="utf-8")
    assert install_skill(source_repository, "sample-skill", target_repository) == destination
    assert contents(destination) == contents(distribution)
    assert set(destination.parent.iterdir()) == {destination}


def test_all_installs_in_name_order_and_preserves_target_only_skills(
    source_repository: Path, target_repository: Path, distribution: Path
) -> None:
    create_distribution(source_repository, "another-skill")
    local = target_repository / ".agents/skills/local-skill"
    local.mkdir(parents=True)
    (local / "SKILL.md").write_text("target-only skill\n", encoding="utf-8")
    previous = contents(local)
    destinations = install_all_skills(source_repository, target_repository)
    assert [p.name for p in destinations] == ["another-skill", "sample-skill"]
    for destination in destinations:
        assert contents(destination) == contents(source_repository / "skills" / destination.name / "dist")
    assert contents(local) == previous
    assert set(local.parent.iterdir()) == {*destinations, local}


def test_all_prevalidates_every_distribution_before_replacing_any_skill(
    source_repository: Path, target_repository: Path, distribution: Path
) -> None:
    invalid = create_distribution(source_repository, "zeta-skill")
    (invalid / "agents/openai.yaml").unlink()
    destination = install_skill(source_repository, "sample-skill", target_repository)
    previous = contents(destination)
    (distribution / "SKILL.md").write_text("new distribution\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        install_all_skills(source_repository, target_repository)
    assert contents(destination) == previous
    assert set(destination.parent.iterdir()) == {destination}


@pytest.mark.parametrize("batch", [False, True])
def test_failed_replacement_restores_current_skill(
    source_repository: Path, target_repository: Path, distribution: Path,
    monkeypatch: pytest.MonkeyPatch, batch: bool,
) -> None:
    names = ["alpha-skill", "sample-skill", "zeta-skill"] if batch else ["sample-skill"]
    previous = {}
    for name in names:
        if name != "sample-skill":
            create_distribution(source_repository, name)
        destination = install_skill(source_repository, name, target_repository)
        previous[name] = contents(destination)
        (source_repository / "skills" / name / "dist/SKILL.md").write_text(
            f"updated {name}\n", encoding="utf-8",
        )
    failed_destination = target_repository / ".agents/skills/sample-skill"
    real_replace = os.replace
    failed = False

    def fail_once_at_destination(source, target):
        nonlocal failed
        # Observe the public destination, leaving temporary paths unconstrained.
        if Path(target) == failed_destination and not failed:
            failed = True
            raise OSError("simulated promotion failure")
        real_replace(source, target)

    monkeypatch.setattr(installer.os, "replace", fail_once_at_destination)
    with pytest.raises(RuntimeError if batch else OSError):
        if batch:
            install_all_skills(source_repository, target_repository)
        else:
            install_skill(source_repository, "sample-skill", target_repository)
    assert failed
    installation_root = failed_destination.parent
    for name in names:
        expected = contents(source_repository / "skills" / name / "dist") if name == "alpha-skill" else previous[name]
        assert contents(installation_root / name) == expected
    assert {p.name for p in installation_root.iterdir()} == set(names)


@pytest.mark.parametrize("empty", [False, True])
def test_all_rejects_missing_or_empty_skills_root(
    source_repository: Path, target_repository: Path, empty: bool
) -> None:
    if empty:
        (source_repository / "skills").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        install_all_skills(source_repository, target_repository)
    assert not (target_repository / ".agents").exists()


@pytest.mark.parametrize("case,error", [
    ("invalid-name", ValueError), ("missing-skill", FileNotFoundError),
    ("missing-target", FileNotFoundError), ("file-target", NotADirectoryError),
    ("missing-metadata", FileNotFoundError),
])
def test_invalid_inputs_do_not_create_an_installation(
    source_repository: Path, target_repository: Path, distribution: Path, case: str, error: type[Exception]
) -> None:
    name, target = "sample-skill", target_repository
    if case == "invalid-name":
        name = "Invalid"
    elif case == "missing-skill":
        name = "missing-skill"
    elif case == "missing-target":
        target = target_repository / "missing"
    elif case == "file-target":
        target = target_repository / "file"
        target.write_text("not a directory\n", encoding="utf-8")
    elif case == "missing-metadata":
        (distribution / "agents/openai.yaml").unlink()
    with pytest.raises(error):
        install_skill(source_repository, name, target)
    assert not (target_repository / ".agents").exists()


@pytest.mark.parametrize("selector", ["sample-skill", "all"])
def test_main_reports_installed_destinations(
    source_repository: Path, target_repository: Path, distribution: Path,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], selector: str,
) -> None:
    if selector == "all":
        create_distribution(source_repository, "another-skill")
    monkeypatch.setattr(installer, "REPOSITORY_ROOT", source_repository)
    monkeypatch.setattr(sys, "argv", ["install_skill.py", selector, str(target_repository)])
    assert installer.main() == 0
    output = capsys.readouterr().out
    names = ["another-skill", "sample-skill"] if selector == "all" else ["sample-skill"]
    positions = []
    for name in names:
        destination = target_repository / ".agents/skills" / name
        assert contents(destination) == contents(source_repository / "skills" / name / "dist")
        positions.append(output.index(str(destination)))
    assert positions == sorted(positions)


def test_scaffold_and_install_commands_need_only_standard_library(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = Path(__file__).resolve().parents[1]
    source = tmp_path / "source"
    shutil.copytree(repository / "scripts", source / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.delenv("PYTHONHOME", raising=False)

    def run(script: str, *args: str):
        # Keep script-local imports while excluding installed site packages.
        command = [sys.executable, "-S", str(source / "scripts" / script), *args]
        result = subprocess.run(command, cwd=target, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        return result

    for name in ("sample-skill", "another-skill"):
        run("create_skill.py", name)
        root = source / "skills" / name
        assert all((root / path).is_file() for path in ("SPEC.md", "README.md", "dist/SKILL.md", "dist/agents/openai.yaml"))
    run("install_skill.py", "sample-skill", str(target))
    installed = target / ".agents/skills/sample-skill"
    (installed / "obsolete.txt").write_text("old\n")
    run("install_skill.py", "all", str(target))
    for name in ("another-skill", "sample-skill"):
        assert contents(target / ".agents/skills" / name) == contents(source / "skills" / name / "dist")
