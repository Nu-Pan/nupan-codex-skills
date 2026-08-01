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
    distribution_root = skill_root / "dist" / skill_name
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

{{{{TODO: スキルが実現する結果と成功条件を記載する}}}}

このファイルは、`{skill_name}` のスキル仕様の正本である。
実行時仕様を変更するときは、先にこのファイルを変更する。

## 適用条件

{{{{TODO: スキルを使用する依頼や状況を記載する}}}}

## 対象外

{{{{TODO: スキルが扱わない依頼や状況を記載する}}}}

## 入力と前提

{{{{TODO: 必要な入力、制約、優先順位を記載する}}}}

## 実行時の規則

{{{{TODO: エージェントが従う規則と手順を記載する}}}}

## 出力

{{{{TODO: 期待する出力と既定形式を記載する}}}}

## 検証

{{{{TODO: 完了前に確認する条件を記載する}}}}
"""


def _readme_template(skill_name: str) -> str:
    return f"""# {skill_name}

{{{{TODO: 利用者向けにスキルの概要を記載する}}}}

仕様の正本は、[`SPEC.md`](SPEC.md) です。
配布物は、[`dist/{skill_name}`](dist/{skill_name}) にあります。
共通の導入方法は、[ルート README のインストール手順](../../README.md#インストール)を参照してください。

## 呼び出し例

{{{{TODO: スキル固有の適用条件と使用方法を記載する}}}}

```text
${skill_name} を使って、{{{{TODO: 具体的な依頼例を記載する}}}}
```
"""


def _skill_template(skill_name: str) -> str:
    return f"""---
name: {skill_name}
description: {{{{TODO: スキルの機能と適用条件を記載する}}}}
---

# {{{{TODO: スキルの動作を表す見出しを記載する}}}}

{{{{TODO: 実行時にエージェントが従う規則を命令形で記載する}}}}
"""


def _openai_template(skill_name: str) -> str:
    return f'''interface:
  display_name: "{{{{TODO: 利用者向けの表示名を記載する}}}}"
  short_description: "{{{{TODO: 25〜64 文字で短い説明を記載する}}}}"
  default_prompt: "${skill_name} を使って、{{{{TODO: 具体的な依頼例を記載する}}}}"
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="新しいスキルの雛形を生成します。")
    parser.add_argument("skill_name", help="小文字、数字、ハイフンからなるスキル名")
    args = parser.parse_args()

    try:
        target = create_skill(REPOSITORY_ROOT, args.skill_name)
    except (FileExistsError, OSError, ValueError) as error:
        parser.exit(1, f"エラー: {error}\n")

    print(f"スキルの雛形を生成しました: {target.relative_to(REPOSITORY_ROOT)}")
    print("SPEC.md から編集し、{{TODO: ...}} をすべて解消してください。")
    print(f"完了前に実行: python3 scripts/validate_skills.py {args.skill_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
