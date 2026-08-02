#!/usr/bin/env python3
"""Shared repository structure and validation helpers."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MIN_SHORT_DESCRIPTION_LENGTH = 25
MAX_SHORT_DESCRIPTION_LENGTH = 64
ALL_SKILLS_SELECTOR = "all"

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_KEY_PATTERN = re.compile(r"^([A-Za-z0-9_-]+):(?:[ \t]+(.*))?$")
INTERFACE_VALUE_PATTERN = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]+(.+)$")
UNRESOLVED_PLACEHOLDER_PATTERN = re.compile(
    r"\{\{todo-[a-z0-9]+(?:-[a-z0-9]+)*\}\}"
)

REQUIRED_RELATIVE_FILES = (
    Path("README.md"),
    Path("SPEC.md"),
    Path("dist") / "SKILL.md",
    Path("dist") / "agents" / "openai.yaml",
)
FORBIDDEN_DISTRIBUTION_FILES = {"README.md", "SPEC.md", "AGENTS.md", "LICENSE"}


@dataclass(frozen=True)
class ValidationIssue:
    """One repository validation failure."""

    path: Path
    message: str

    def format(self, repository_root: Path) -> str:
        try:
            display_path = self.path.relative_to(repository_root)
        except ValueError:
            display_path = self.path
        return f"{display_path}: {self.message}"


def skill_name_error(skill_name: str) -> str | None:
    """Return a validation error for a skill name, if any."""

    if not skill_name:
        return "スキル名を空にできません"
    if len(skill_name) > MAX_SKILL_NAME_LENGTH:
        return f"スキル名は {MAX_SKILL_NAME_LENGTH} 文字以内にしてください"
    if not SKILL_NAME_PATTERN.fullmatch(skill_name):
        return "スキル名には小文字の英字、数字、単独のハイフンだけを使用してください"
    if skill_name == ALL_SKILLS_SELECTOR:
        return f"{ALL_SKILLS_SELECTOR} は全スキルを指定する予約語です"
    return None


def validate_repository(
    repository_root: Path,
    requested_skill_names: Iterable[str] | None = None,
) -> tuple[list[str], list[ValidationIssue]]:
    """Validate selected skills, or every skill when none are selected."""

    repository_root = repository_root.resolve()
    skills_root = repository_root / "skills"
    issues: list[ValidationIssue] = []

    if not skills_root.is_dir():
        return [], [ValidationIssue(skills_root, "skills ディレクトリがありません")]

    if requested_skill_names:
        skill_names = list(dict.fromkeys(requested_skill_names))
    else:
        skill_names = []
        for entry in sorted(skills_root.iterdir(), key=lambda path: path.name):
            if not entry.is_dir():
                issues.append(
                    ValidationIssue(entry, "skills 直下にはスキルディレクトリだけを置いてください")
                )
                continue
            skill_names.append(entry.name)

        if not skill_names:
            issues.append(ValidationIssue(skills_root, "検証対象のスキルがありません"))

    validated_names: list[str] = []
    for skill_name in skill_names:
        name_error = skill_name_error(skill_name)
        if name_error:
            issues.append(ValidationIssue(skills_root / skill_name, name_error))
            continue

        validated_names.append(skill_name)
        issues.extend(validate_skill(repository_root, skill_name))

    issues.extend(_validate_root_readme(repository_root, validated_names))
    return validated_names, issues


def validate_skill(repository_root: Path, skill_name: str) -> list[ValidationIssue]:
    """Validate one skill against the common repository specification."""

    skill_root = repository_root / "skills" / skill_name
    issues: list[ValidationIssue] = []

    if not skill_root.is_dir():
        return [ValidationIssue(skill_root, "スキルディレクトリがありません")]

    required_files = tuple(
        skill_root / Path(str(relative_path).format(skill_name=skill_name))
        for relative_path in REQUIRED_RELATIVE_FILES
    )
    for required_file in required_files:
        if not required_file.is_file():
            issues.append(ValidationIssue(required_file, "必須ファイルがありません"))

    distribution_root = skill_root / "dist"
    legacy_distribution_root = distribution_root / skill_name
    if legacy_distribution_root.exists() or legacy_distribution_root.is_symlink():
        issues.append(
            ValidationIssue(
                legacy_distribution_root,
                "配布物は dist 直下へ配置し、同名の配布用ディレクトリを追加しないでください",
            )
        )

    if distribution_root.is_dir():
        for entry in distribution_root.rglob("*"):
            if entry.is_file() and entry.name in FORBIDDEN_DISTRIBUTION_FILES:
                issues.append(ValidationIssue(entry, "保守用ファイルを配布物に含められません"))

    text_files = list(required_files)
    optional_agents = skill_root / "AGENTS.md"
    if optional_agents.exists():
        if optional_agents.is_file():
            text_files.append(optional_agents)
        else:
            issues.append(ValidationIssue(optional_agents, "AGENTS.md はファイルとして配置してください"))

    issues.extend(_validate_text_files(text_files))

    skill_file = distribution_root / "SKILL.md"
    if skill_file.is_file():
        issues.extend(_validate_skill_file(skill_file, skill_name))

    openai_file = distribution_root / "agents" / "openai.yaml"
    if openai_file.is_file():
        issues.extend(_validate_openai_file(openai_file, skill_name))

    readme_file = skill_root / "README.md"
    if readme_file.is_file():
        issues.extend(_validate_skill_readme(readme_file, skill_name))

    return issues


def _read_text(path: Path) -> tuple[str | None, ValidationIssue | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError) as error:
        return None, ValidationIssue(path, f"UTF-8 のテキストとして読めません: {error}")


def _validate_text_files(paths: Iterable[Path]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for path in paths:
        if not path.is_file():
            continue
        content, read_issue = _read_text(path)
        if read_issue:
            issues.append(read_issue)
            continue
        assert content is not None
        if not content.strip():
            issues.append(ValidationIssue(path, "ファイルを空にできません"))
        if UNRESOLVED_PLACEHOLDER_PATTERN.search(content):
            issues.append(
                ValidationIssue(
                    path,
                    "todo- で始まる未解消のプレースホルダーが残っています",
                )
            )
    return issues


def _validate_skill_file(path: Path, skill_name: str) -> list[ValidationIssue]:
    content, read_issue = _read_text(path)
    if read_issue:
        return [read_issue]
    assert content is not None

    issues: list[ValidationIssue] = []
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return [ValidationIssue(path, "YAML frontmatter をファイル先頭に配置してください")]

    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        return [ValidationIssue(path, "YAML frontmatter の終了行がありません")]

    values: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():
            issues.append(ValidationIssue(path, "frontmatter の値は 1 行で記載してください"))
            continue
        match = FRONTMATTER_KEY_PATTERN.fullmatch(line)
        if not match:
            issues.append(ValidationIssue(path, f"frontmatter の行を解釈できません: {line}"))
            continue
        key, raw_value = match.groups()
        if key in values:
            issues.append(ValidationIssue(path, f"frontmatter の {key} が重複しています"))
            continue
        values[key] = _decode_scalar(raw_value or "")

    expected_keys = {"name", "description"}
    missing_keys = expected_keys - values.keys()
    unexpected_keys = values.keys() - expected_keys
    for key in sorted(missing_keys):
        issues.append(ValidationIssue(path, f"frontmatter に {key} がありません"))
    for key in sorted(unexpected_keys):
        issues.append(ValidationIssue(path, f"frontmatter に不要な {key} があります"))

    name = values.get("name", "").strip()
    if "name" in values and not name:
        issues.append(ValidationIssue(path, "name を空にできません"))
    elif name and name != skill_name:
        issues.append(ValidationIssue(path, f"name を {skill_name} と一致させてください"))

    description = values.get("description", "").strip()
    if "description" in values and not description:
        issues.append(ValidationIssue(path, "description を空にできません"))
    if len(description) > MAX_DESCRIPTION_LENGTH:
        issues.append(
            ValidationIssue(path, f"description は {MAX_DESCRIPTION_LENGTH} 文字以内にしてください")
        )
    if "<" in description or ">" in description:
        issues.append(ValidationIssue(path, "description に山括弧を使用できません"))

    if not "\n".join(lines[closing_index + 1 :]).strip():
        issues.append(ValidationIssue(path, "frontmatter の後にスキル本文を記載してください"))
    return issues


def _decode_scalar(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        try:
            decoded = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value
        if isinstance(decoded, str):
            return decoded
    return value


def _validate_openai_file(path: Path, skill_name: str) -> list[ValidationIssue]:
    content, read_issue = _read_text(path)
    if read_issue:
        return [read_issue]
    assert content is not None

    issues: list[ValidationIssue] = []
    lines = content.splitlines()
    if any("\t" in line[: len(line) - len(line.lstrip())] for line in lines):
        issues.append(ValidationIssue(path, "インデントには空白を使用してください"))

    try:
        interface_index = lines.index("interface:")
    except ValueError:
        return issues + [ValidationIssue(path, "interface セクションがありません")]

    interface_values: dict[str, str] = {}
    for line in lines[interface_index + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            break
        match = INTERFACE_VALUE_PATTERN.fullmatch(line)
        if not match:
            continue
        key, raw_value = match.groups()
        if key in interface_values:
            issues.append(ValidationIssue(path, f"interface.{key} が重複しています"))
            continue
        if not _is_quoted_string(raw_value):
            issues.append(ValidationIssue(path, f"interface.{key} の文字列を引用符で囲んでください"))
        interface_values[key] = _decode_scalar(raw_value)

    required_keys = {"display_name", "short_description", "default_prompt"}
    for key in sorted(required_keys - interface_values.keys()):
        issues.append(ValidationIssue(path, f"interface.{key} がありません"))

    display_name = interface_values.get("display_name", "").strip()
    if "display_name" in interface_values and not display_name:
        issues.append(ValidationIssue(path, "interface.display_name を空にできません"))

    short_description = interface_values.get("short_description", "").strip()
    if "short_description" in interface_values and not (
        MIN_SHORT_DESCRIPTION_LENGTH <= len(short_description) <= MAX_SHORT_DESCRIPTION_LENGTH
    ):
        issues.append(
            ValidationIssue(
                path,
                "interface.short_description は "
                f"{MIN_SHORT_DESCRIPTION_LENGTH}〜{MAX_SHORT_DESCRIPTION_LENGTH} 文字にしてください",
            )
        )

    default_prompt = interface_values.get("default_prompt", "")
    if "default_prompt" in interface_values and f"${skill_name}" not in default_prompt:
        issues.append(
            ValidationIssue(path, f"interface.default_prompt に ${skill_name} を含めてください")
        )
    return issues


def _is_quoted_string(raw_value: str) -> bool:
    value = raw_value.strip()
    return len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}


def _validate_skill_readme(path: Path, skill_name: str) -> list[ValidationIssue]:
    content, read_issue = _read_text(path)
    if read_issue:
        return [read_issue]
    assert content is not None

    required_fragments = {
        "SPEC.md": "仕様の正本へのリンクを記載してください",
        "(dist)": "配布物へのパスを記載してください",
    }
    issues = [
        ValidationIssue(path, message)
        for fragment, message in required_fragments.items()
        if fragment not in content
    ]
    if f"${skill_name}" in content:
        issues.append(
            ValidationIssue(
                path,
                "明示的な呼び出し方法はルート README だけに記載してください",
            )
        )
    return issues


def _validate_root_readme(
    repository_root: Path,
    skill_names: Iterable[str],
) -> list[ValidationIssue]:
    path = repository_root / "README.md"
    content, read_issue = _read_text(path)
    if read_issue:
        return [read_issue]
    assert content is not None

    issues = [
        ValidationIssue(path, f"収録スキル一覧に {skill_name} へのリンクがありません")
        for skill_name in skill_names
        if f"skills/{skill_name}/README.md" not in content
    ]

    required_fragments = {
        "python3 scripts/install_skill.py {{skill-name}} {{target-repository}}": (
            "共通インストール手順に正規のスクリプト呼び出しを記載してください"
        ),
        "python3 scripts/install_skill.py all {{target-repository}}": (
            "全スキルのインストール手順を記載してください"
        ),
        ".agents/skills/{{skill-name}}": "共通インストール先を記載してください",
        "${{skill-name}}": "スキルに共通する呼び出し方法を記載してください",
    }
    issues.extend(
        ValidationIssue(path, message)
        for fragment, message in required_fragments.items()
        if fragment not in content
    )
    return issues
