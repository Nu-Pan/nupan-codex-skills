#!/usr/bin/env python3
"""Validate repository-wide skill independence and composition metadata."""

from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


COMPOSITION_FILE_NAME = "skill-composition.json"
COMPOSITION_VERSION = 1
SPEC_COMPOSITION_HEADING = "## 独立性と合成"

ROOT_KEYS = {
    "version",
    "optional_references",
    "standalone_scenarios",
    "combination_scenarios",
    "pairs",
}
OPTIONAL_REFERENCE_KEYS = {"source", "target", "locations", "fallback"}
STANDALONE_SCENARIO_KEYS = {"id", "skill", "request", "expected", "forbidden"}
COMBINATION_SCENARIO_KEYS = {"id", "skills", "request", "expected", "forbidden"}
PAIR_KEYS = {"skills", "relation", "scenario_ids"}
PAIR_RELATIONS = {"orthogonal", "overlap"}

SCENARIO_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HYPHENATED_SKILL_REFERENCE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9-])\$([a-z0-9]+(?:-[a-z0-9]+)+)(?![A-Za-z0-9-])"
)
SKILL_PATH_REFERENCE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_{-])(?:\.agents/)?skills/"
    r"([a-z0-9]+(?:-[a-z0-9]+)*)(?![A-Za-z0-9-])"
)
TEXT_RESOURCE_SUFFIXES = {".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}

CompositionIssue = tuple[Path, str]


class DuplicateJsonKeyError(ValueError):
    """Raised when a JSON object repeats a key."""


def validate_skill_composition(
    repository_root: Path,
    skill_names: Iterable[str],
) -> list[CompositionIssue]:
    """Validate the composition registry and repository skill references."""

    repository_root = repository_root.resolve()
    names = sorted(set(skill_names))
    registry_path = repository_root / COMPOSITION_FILE_NAME
    issues: list[CompositionIssue] = []

    data = _load_registry(registry_path, issues)
    if data is None:
        issues.extend(_validate_spec_composition_headings(repository_root, names))
        issues.extend(_validate_repository_path_references(repository_root, names))
        return issues

    _validate_exact_keys(data, ROOT_KEYS, registry_path, "ルート object", issues)
    if data.get("version") != COMPOSITION_VERSION:
        issues.append(
            (
                registry_path,
                f"version は整数の {COMPOSITION_VERSION} にしてください",
            )
        )

    standalone, standalone_ids = _validate_standalone_scenarios(
        data.get("standalone_scenarios"), names, registry_path, issues
    )
    combinations_by_id, combination_ids = _validate_combination_scenarios(
        data.get("combination_scenarios"), names, registry_path, issues
    )

    duplicate_ids = standalone_ids & combination_ids
    for scenario_id in sorted(duplicate_ids):
        issues.append((registry_path, f"シナリオ ID が重複しています: {scenario_id}"))

    optional_references = _validate_optional_references(
        data.get("optional_references"), repository_root, names, registry_path, issues
    )
    _validate_pairs(
        data.get("pairs"),
        names,
        combinations_by_id,
        registry_path,
        issues,
    )

    if standalone is not None:
        scenario_skills = [scenario["skill"] for scenario in standalone if "skill" in scenario]
        if scenario_skills != sorted(scenario_skills):
            issues.append((registry_path, "standalone_scenarios を skill の名前順にしてください"))

    issues.extend(_validate_spec_composition_headings(repository_root, names))
    issues.extend(_validate_repository_path_references(repository_root, names))
    issues.extend(
        _validate_cross_skill_references(
            repository_root,
            names,
            optional_references,
        )
    )
    return issues


def _load_registry(path: Path, issues: list[CompositionIssue]) -> dict[str, Any] | None:
    if not path.is_file():
        issues.append((path, "組み合わせ台帳がありません"))
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        issues.append((path, f"UTF-8 の JSON として読めません: {error}"))
        return None

    try:
        data = json.loads(content, object_pairs_hook=_reject_duplicate_json_keys)
    except DuplicateJsonKeyError as error:
        issues.append((path, str(error)))
        return None
    except json.JSONDecodeError as error:
        issues.append((path, f"JSON を解釈できません: {error.msg}（{error.lineno} 行目）"))
        return None

    if not isinstance(data, dict):
        issues.append((path, "ルートは JSON object にしてください"))
        return None
    return data


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"JSON object のキーが重複しています: {key}")
        result[key] = value
    return result


def _validate_exact_keys(
    value: dict[str, Any],
    expected: set[str],
    path: Path,
    label: str,
    issues: list[CompositionIssue],
) -> None:
    for key in sorted(expected - value.keys()):
        issues.append((path, f"{label} に {key} がありません"))
    for key in sorted(value.keys() - expected):
        issues.append((path, f"{label} に不要な {key} があります"))


def _require_object_list(
    value: Any,
    field: str,
    path: Path,
    issues: list[CompositionIssue],
) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        issues.append((path, f"{field} は JSON array にしてください"))
        return None
    if any(not isinstance(item, dict) for item in value):
        issues.append((path, f"{field} の各要素は JSON object にしてください"))
        return None
    return value


def _validate_non_empty_string(
    value: Any,
    field: str,
    path: Path,
    issues: list[CompositionIssue],
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        issues.append((path, f"{field} は空でない文字列にしてください"))
        return None
    return value


def _validate_string_list(
    value: Any,
    field: str,
    path: Path,
    issues: list[CompositionIssue],
    *,
    min_items: int = 0,
    require_sorted: bool = False,
) -> list[str] | None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        issues.append((path, f"{field} は空でない文字列の array にしてください"))
        return None
    if len(value) < min_items:
        issues.append((path, f"{field} には {min_items} 件以上を記載してください"))
    if len(value) != len(set(value)):
        issues.append((path, f"{field} に重複があります"))
    if require_sorted and value != sorted(value):
        issues.append((path, f"{field} を名前順にしてください"))
    return value


def _validate_scenario_common(
    scenario: dict[str, Any],
    label: str,
    path: Path,
    issues: list[CompositionIssue],
) -> str | None:
    scenario_id = _validate_non_empty_string(scenario.get("id"), f"{label}.id", path, issues)
    if scenario_id is not None and not SCENARIO_ID_PATTERN.fullmatch(scenario_id):
        issues.append((path, f"{label}.id の形式が不正です: {scenario_id}"))

    _validate_non_empty_string(scenario.get("request"), f"{label}.request", path, issues)
    _validate_string_list(
        scenario.get("expected"), f"{label}.expected", path, issues, min_items=1
    )
    _validate_string_list(
        scenario.get("forbidden"), f"{label}.forbidden", path, issues, min_items=1
    )
    return scenario_id


def _validate_standalone_scenarios(
    value: Any,
    skill_names: list[str],
    path: Path,
    issues: list[CompositionIssue],
) -> tuple[list[dict[str, Any]] | None, set[str]]:
    scenarios = _require_object_list(value, "standalone_scenarios", path, issues)
    if scenarios is None:
        return None, set()

    ids: set[str] = set()
    scenario_skills: list[str] = []
    known_names = set(skill_names)
    for index, scenario in enumerate(scenarios):
        label = f"standalone_scenarios[{index}]"
        _validate_exact_keys(scenario, STANDALONE_SCENARIO_KEYS, path, label, issues)
        scenario_id = _validate_scenario_common(scenario, label, path, issues)
        if scenario_id is not None:
            if scenario_id in ids:
                issues.append((path, f"シナリオ ID が重複しています: {scenario_id}"))
            ids.add(scenario_id)

        skill = _validate_non_empty_string(scenario.get("skill"), f"{label}.skill", path, issues)
        if skill is not None:
            scenario_skills.append(skill)
            if skill not in known_names:
                issues.append((path, f"単独シナリオが未知のスキルを参照しています: {skill}"))

    for skill_name in sorted(known_names - set(scenario_skills)):
        issues.append((path, f"単独シナリオがありません: {skill_name}"))
    for skill_name in sorted({name for name in scenario_skills if scenario_skills.count(name) > 1}):
        issues.append((path, f"単独シナリオが重複しています: {skill_name}"))
    return scenarios, ids


def _validate_combination_scenarios(
    value: Any,
    skill_names: list[str],
    path: Path,
    issues: list[CompositionIssue],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    scenarios = _require_object_list(value, "combination_scenarios", path, issues)
    if scenarios is None:
        return {}, set()

    by_id: dict[str, dict[str, Any]] = {}
    ids: set[str] = set()
    ordered_ids: list[str] = []
    known_names = set(skill_names)
    for index, scenario in enumerate(scenarios):
        label = f"combination_scenarios[{index}]"
        _validate_exact_keys(scenario, COMBINATION_SCENARIO_KEYS, path, label, issues)
        scenario_id = _validate_scenario_common(scenario, label, path, issues)
        if scenario_id is not None:
            ordered_ids.append(scenario_id)
            if scenario_id in ids:
                issues.append((path, f"シナリオ ID が重複しています: {scenario_id}"))
            else:
                by_id[scenario_id] = scenario
            ids.add(scenario_id)

        skills = _validate_string_list(
            scenario.get("skills"),
            f"{label}.skills",
            path,
            issues,
            min_items=2,
            require_sorted=True,
        )
        if skills is not None:
            for skill_name in sorted(set(skills) - known_names):
                issues.append((path, f"組み合わせシナリオが未知のスキルを参照しています: {skill_name}"))

    if ordered_ids != sorted(ordered_ids):
        issues.append((path, "combination_scenarios を id の名前順にしてください"))
    return by_id, ids


def _validate_optional_references(
    value: Any,
    repository_root: Path,
    skill_names: list[str],
    path: Path,
    issues: list[CompositionIssue],
) -> set[tuple[str, str, str]]:
    references = _require_object_list(value, "optional_references", path, issues)
    if references is None:
        return set()

    known_names = set(skill_names)
    declared: set[tuple[str, str, str]] = set()
    order_keys: list[tuple[str, str, tuple[str, ...]]] = []
    for index, reference in enumerate(references):
        label = f"optional_references[{index}]"
        _validate_exact_keys(reference, OPTIONAL_REFERENCE_KEYS, path, label, issues)
        source = _validate_non_empty_string(
            reference.get("source"), f"{label}.source", path, issues
        )
        target = _validate_non_empty_string(
            reference.get("target"), f"{label}.target", path, issues
        )
        locations = _validate_string_list(
            reference.get("locations"),
            f"{label}.locations",
            path,
            issues,
            min_items=1,
            require_sorted=True,
        )
        _validate_non_empty_string(reference.get("fallback"), f"{label}.fallback", path, issues)

        if source is None or target is None or locations is None:
            continue
        order_keys.append((source, target, tuple(locations)))
        if source not in known_names:
            issues.append((path, f"任意参照の source が存在しません: {source}"))
        if target not in known_names:
            issues.append((path, f"任意参照の target が存在しません: {target}"))
        if source == target:
            issues.append((path, f"任意参照の source と target を分けてください: {source}"))

        for location in locations:
            relative_path = Path(location)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                issues.append((path, f"任意参照の locations は安全な相対パスにしてください: {location}"))
                continue
            key = (source, target, relative_path.as_posix())
            if key in declared:
                issues.append((path, f"任意参照が重複しています: {source} -> {target} ({location})"))
            declared.add(key)

            source_path = repository_root / "skills" / source / relative_path
            if source in known_names and not source_path.is_file():
                issues.append((path, f"任意参照の locations が存在しません: {source}/{location}"))

    if order_keys != sorted(order_keys):
        issues.append((path, "optional_references を source、target、locations の名前順にしてください"))
    return declared


def _validate_pairs(
    value: Any,
    skill_names: list[str],
    combinations_by_id: dict[str, dict[str, Any]],
    path: Path,
    issues: list[CompositionIssue],
) -> None:
    pairs = _require_object_list(value, "pairs", path, issues)
    if pairs is None:
        return

    known_names = set(skill_names)
    observed: set[tuple[str, str]] = set()
    ordered_pairs: list[tuple[str, str]] = []
    referenced_scenarios: set[str] = set()
    for index, pair in enumerate(pairs):
        label = f"pairs[{index}]"
        _validate_exact_keys(pair, PAIR_KEYS, path, label, issues)
        skills = _validate_string_list(
            pair.get("skills"),
            f"{label}.skills",
            path,
            issues,
            min_items=2,
            require_sorted=True,
        )
        if skills is None or len(skills) != 2 or len(set(skills)) != 2:
            issues.append((path, f"{label}.skills には異なる二つのスキルを記載してください"))
            pair_key = None
        else:
            pair_key = (skills[0], skills[1])
            ordered_pairs.append(pair_key)
            if pair_key in observed:
                issues.append((path, f"pair が重複しています: {skills[0]}, {skills[1]}"))
            observed.add(pair_key)
            for skill_name in sorted(set(skills) - known_names):
                issues.append((path, f"pair が未知のスキルを参照しています: {skill_name}"))

        relation = pair.get("relation")
        if relation not in PAIR_RELATIONS:
            issues.append((path, f"{label}.relation は orthogonal または overlap にしてください"))

        scenario_ids = _validate_string_list(
            pair.get("scenario_ids"),
            f"{label}.scenario_ids",
            path,
            issues,
            require_sorted=True,
        )
        if scenario_ids is None:
            continue
        if relation == "orthogonal" and scenario_ids:
            issues.append((path, f"{label} の orthogonal pair では scenario_ids を空にしてください"))
        if relation == "overlap" and not scenario_ids:
            issues.append((path, f"{label} の overlap pair には scenario_ids が必要です"))

        for scenario_id in scenario_ids:
            referenced_scenarios.add(scenario_id)
            scenario = combinations_by_id.get(scenario_id)
            if scenario is None:
                issues.append((path, f"pair が未知の組み合わせシナリオを参照しています: {scenario_id}"))
                continue
            scenario_skills = scenario.get("skills")
            if pair_key is not None and isinstance(scenario_skills, list):
                if not set(pair_key).issubset(scenario_skills):
                    issues.append(
                        (
                            path,
                            f"{scenario_id} に pair の両スキルがありません: "
                            f"{pair_key[0]}, {pair_key[1]}",
                        )
                    )

    if ordered_pairs != sorted(ordered_pairs):
        issues.append((path, "pairs をスキル名の組の名前順にしてください"))

    expected_pairs = set(combinations(skill_names, 2))
    for missing_pair in sorted(expected_pairs - observed):
        issues.append((path, f"pair がありません: {missing_pair[0]}, {missing_pair[1]}"))
    for unexpected_pair in sorted(observed - expected_pairs):
        issues.append((path, f"不要な pair があります: {unexpected_pair[0]}, {unexpected_pair[1]}"))

    for scenario_id in sorted(combinations_by_id.keys() - referenced_scenarios):
        issues.append((path, f"どの overlap pair からも参照されないシナリオがあります: {scenario_id}"))


def _validate_spec_composition_headings(
    repository_root: Path,
    skill_names: list[str],
) -> list[CompositionIssue]:
    issues: list[CompositionIssue] = []
    for skill_name in skill_names:
        spec_path = repository_root / "skills" / skill_name / "SPEC.md"
        if not spec_path.is_file():
            continue
        try:
            lines = spec_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        if SPEC_COMPOSITION_HEADING not in lines:
            issues.append(
                (
                    spec_path,
                    f"合成規則の見出し {SPEC_COMPOSITION_HEADING} がありません",
                )
            )
    return issues


def _repository_text_paths(repository_root: Path, skill_names: list[str]) -> list[Path]:
    paths: set[Path] = set()
    for path in (repository_root / "AGENTS.md", repository_root / "README.md"):
        if path.is_file():
            paths.add(path)
    docs_root = repository_root / "docs"
    if docs_root.is_dir():
        paths.update(path for path in docs_root.rglob("*.md") if path.is_file())

    for skill_name in skill_names:
        skill_root = repository_root / "skills" / skill_name
        for name in ("AGENTS.md", "README.md", "SPEC.md"):
            path = skill_root / name
            if path.is_file():
                paths.add(path)
        distribution_root = skill_root / "dist"
        if distribution_root.is_dir():
            paths.update(
                path
                for path in distribution_root.rglob("*")
                if path.is_file() and path.suffix.lower() in TEXT_RESOURCE_SUFFIXES
            )
    return sorted(paths)


def _validate_repository_path_references(
    repository_root: Path,
    skill_names: list[str],
) -> list[CompositionIssue]:
    issues: list[CompositionIssue] = []
    known_names = set(skill_names)
    skills_root = repository_root / "skills"
    reported: set[tuple[Path, str, str]] = set()
    for path in _repository_text_paths(repository_root, skill_names):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        owner = _skill_owner(path, skills_root, known_names)
        for match in SKILL_PATH_REFERENCE_PATTERN.finditer(content):
            target = match.group(1)
            if target not in known_names:
                key = (path, target, "missing")
                if key not in reported:
                    issues.append((path, f"存在しないスキルへのパス参照があります: {target}"))
                    reported.add(key)
            elif owner is not None and owner != target:
                key = (path, target, "direct")
                if key not in reported:
                    issues.append(
                        (
                            path,
                            f"別のスキルへの直接パス参照は使用できません: {owner} -> {target}",
                        )
                    )
                    reported.add(key)
    return issues


def _skill_owner(path: Path, skills_root: Path, known_names: set[str]) -> str | None:
    try:
        relative = path.relative_to(skills_root)
    except ValueError:
        return None
    if not relative.parts or relative.parts[0] not in known_names:
        return None
    return relative.parts[0]


def _validate_cross_skill_references(
    repository_root: Path,
    skill_names: list[str],
    declared: set[tuple[str, str, str]],
) -> list[CompositionIssue]:
    issues: list[CompositionIssue] = []
    known_names = set(skill_names)
    observed: set[tuple[str, str, str]] = set()
    skills_root = repository_root / "skills"

    for path in _repository_text_paths(repository_root, skill_names):
        owner = _skill_owner(path, skills_root, known_names)
        if owner is None:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        relative_path = path.relative_to(skills_root / owner).as_posix()

        for target in skill_names:
            if target == owner:
                continue
            target_pattern = re.compile(
                rf"(?<![A-Za-z0-9-])(\$?){re.escape(target)}(?![A-Za-z0-9-])"
            )
            for match in target_pattern.finditer(content):
                key = (owner, target, relative_path)
                if match.group(1) != "$":
                    issues.append(
                        (
                            path,
                            f"別のスキル名は $ を付けた任意参照として記載してください: {target}",
                        )
                    )
                    continue
                observed.add(key)
                if key not in declared:
                    issues.append(
                        (
                            path,
                            f"台帳にない任意参照があります: {owner} -> {target}",
                        )
                    )

        for match in HYPHENATED_SKILL_REFERENCE_PATTERN.finditer(content):
            target = match.group(1)
            if target != owner and target not in known_names:
                issues.append((path, f"存在しないスキルへの任意参照があります: {target}"))

    for source, target, location in sorted(declared - observed):
        issues.append(
            (
                repository_root / "skills" / source / location,
                f"台帳に記載された任意参照がファイルにありません: {source} -> {target}",
            )
        )
    return issues
