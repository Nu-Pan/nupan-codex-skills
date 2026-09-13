"""Skill identifiers shared by installation, scaffolding, and validation."""

from __future__ import annotations

import re


MAX_SKILL_NAME_LENGTH = 64
ALL_SKILLS_SELECTOR = "all"
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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
