#!/usr/bin/env python3
"""Create a repository skill scaffold without overwriting existing files."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from skill_repository import skill_name_error


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def create_skill(repository_root: Path, skill_name: str) -> Path:
    """Create one skill scaffold and return its final path."""

    name_error = skill_name_error(skill_name)
    if name_error:
        raise ValueError(name_error)

    skills_root = repository_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    target = skills_root / skill_name
    if target.exists():
        raise FileExistsError(f"既存のパスを上書きできません: {target}")

    temporary_root = Path(tempfile.mkdtemp(prefix=f".{skill_name}-", dir=skills_root))
    temporary_skill = temporary_root / skill_name
    try:
        _write_scaffold(temporary_skill, skill_name)
        temporary_skill.replace(target)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
    return target


def _write_scaffold(skill_root: Path, skill_name: str) -> None:
    distribution_root = skill_root / "dist"
    agents_root = distribution_root / "agents"
    agents_root.mkdir(parents=True)

    (skill_root / "SPEC.md").write_text(_spec_template(skill_name), encoding="utf-8")
    (skill_root / "README.md").write_text(_readme_template(skill_name), encoding="utf-8")
    (distribution_root / "SKILL.md").write_text(
        _skill_template(skill_name), encoding="utf-8"
    )
    (agents_root / "openai.yaml").write_text(
        _openai_template(skill_name), encoding="utf-8"
    )


def _spec_template(skill_name: str) -> str:
    return f"""# {skill_name} の仕様

## 目的

{{{{todo-skill-goal-and-success-criteria}}}}

このファイルは、`{skill_name}` のスキル仕様の正本である。
実行時仕様を変更するときは、先にこのファイルを変更する。

## 適用条件

{{{{todo-skill-usage-scenarios}}}}

## 対象外

{{{{todo-out-of-scope-requests-and-scenarios}}}}

## 入力と前提

{{{{todo-required-inputs-constraints-and-priorities}}}}

## 独立性と合成

{{{{todo-standalone-and-composition-rules}}}}

## 実行時の規則

{{{{todo-runtime-rules-and-procedures}}}}

## 出力

{{{{todo-expected-output-and-default-format}}}}

## 検証

{{{{todo-completion-checks}}}}
"""


def _readme_template(skill_name: str) -> str:
    return f"""# {skill_name}

{{{{todo-user-facing-skill-summary}}}}

仕様の正本は、[`SPEC.md`](SPEC.md) です。
配布物は、[`dist`](dist) にあります。
"""


def _skill_template(skill_name: str) -> str:
    return f"""---
name: {skill_name}
description: "{{{{todo-skill-capability-and-usage-conditions}}}}"
---

# {{{{todo-skill-action-heading}}}}

## 実行

{{{{todo-runtime-imperative-instructions}}}}
"""


def _openai_template(skill_name: str) -> str:
    return f'''interface:
  display_name: "{{{{todo-user-facing-display-name}}}}"
  short_description: "{{{{todo-short-description}}}}"
  default_prompt: "${skill_name} を使って、{{{{todo-concrete-request-example}}}}"
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="新しいスキルの雛形を生成します。")
    parser.add_argument(
        "skill_name",
        help="小文字、数字、ハイフンからなるスキル名（all を除く）",
    )
    args = parser.parse_args()

    try:
        target = create_skill(REPOSITORY_ROOT, args.skill_name)
    except (FileExistsError, OSError, ValueError) as error:
        parser.exit(1, f"エラー: {error}\n")

    print(f"スキルの雛形を生成しました: {target.relative_to(REPOSITORY_ROOT)}")
    print("SPEC.md から編集し、todo- で始まるプレースホルダーをすべて解消してください。")
    print(f"完了前に実行: python3 scripts/validate_skills.py {args.skill_name}")
    print("skill-composition.json の単独シナリオと全スキル対も更新してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
