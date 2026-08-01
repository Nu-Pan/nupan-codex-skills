#!/usr/bin/env python3
"""Validate repository skills against the common specification."""

from __future__ import annotations

import argparse
from pathlib import Path

from skill_repository import validate_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="指定したスキル、または全スキルの構造とメタデータを検証します。"
    )
    parser.add_argument("skill_names", nargs="*", help="検証するスキル名")
    args = parser.parse_args()

    skill_names, issues = validate_repository(REPOSITORY_ROOT, args.skill_names)
    if issues:
        print(f"検証に失敗しました（{len(issues)} 件）:")
        for issue in issues:
            print(f"- {issue.format(REPOSITORY_ROOT)}")
        return 1

    for skill_name in skill_names:
        print(f"OK: skills/{skill_name}")
    print(f"検証に成功しました（{len(skill_names)} スキル）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
