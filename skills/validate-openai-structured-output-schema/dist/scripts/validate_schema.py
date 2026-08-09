#!/usr/bin/env python3
"""Validate JSON Schema files against an OpenAI Structured Outputs profile."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes


PROFILE = "openai-structured-outputs-2026-08"
MAX_PROPERTIES = 5_000
MAX_OBJECT_DEPTH = 10
MAX_TOTAL_STRING_LENGTH = 120_000
MAX_ENUM_VALUES = 1_000
LARGE_ENUM_THRESHOLD = 250
MAX_LARGE_ENUM_STRING_LENGTH = 15_000

SUPPORTED_TYPES = {
    "string",
    "number",
    "integer",
    "boolean",
    "object",
    "array",
    "null",
}
SUPPORTED_FORMATS = {
    "date-time",
    "time",
    "date",
    "duration",
    "email",
    "hostname",
    "ipv4",
    "ipv6",
    "uuid",
}
UNSUPPORTED_KEYWORDS = {
    "allOf",
    "oneOf",
    "not",
    "dependentRequired",
    "dependentSchemas",
    "if",
    "then",
    "else",
}
COMMON_TYPED_KEYWORDS = {"type", "description", "enum", "const", "$defs"}
TYPE_KEYWORDS = {
    "object": {"properties", "required", "additionalProperties"},
    "array": {"items", "minItems", "maxItems"},
    "string": {"pattern", "format"},
    "number": {
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
    },
    "integer": {
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
    },
    "boolean": set(),
    "null": set(),
}
ALL_SUPPORTED_KEYWORDS = (
    COMMON_TYPED_KEYWORDS
    | {"anyOf", "$ref"}
    | set().union(*TYPE_KEYWORDS.values())
)


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic schema diagnostic."""

    code: str
    schema_pointer: str
    message: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "schemaPointer": self.schema_pointer,
            "message": self.message,
            "details": self.details,
        }


class DuplicateKeyError(ValueError):
    """Raised when a JSON object repeats a key."""


class InvalidConstantError(ValueError):
    """Raised when JSON contains a non-standard numeric constant."""


class SchemaValidator:
    """Validate one decoded JSON document against the bundled profile."""

    def __init__(self, document: Any) -> None:
        self.document = document
        self.diagnostics: list[Diagnostic] = []
        self._visited_nodes: set[int] = set()
        self._definition_entries: list[dict[str, Any]] = []
        self._definition_ids: set[int] = set()
        self._references: list[tuple[str, Any]] = []
        self._property_count = 0
        self._total_string_length = 0
        self._enum_value_count = 0

    def validate(self) -> list[Diagnostic]:
        if not isinstance(self.document, dict):
            self._add(
                "ROOT_OBJECT_REQUIRED",
                "/",
                "The root schema must be an object with type 'object'.",
                {"actualType": _json_type_name(self.document)},
            )
            return self._sorted_diagnostics()

        if self.document.get("type") != "object":
            self._add(
                "ROOT_OBJECT_REQUIRED",
                "/",
                "The root schema must declare type 'object'.",
                {"actualType": self.document.get("type")},
            )
        if "anyOf" in self.document:
            self._add(
                "ROOT_ANY_OF_FORBIDDEN",
                "/",
                "The root schema must not use anyOf.",
            )

        self._visit(self.document, "/")
        self._validate_references()
        self._validate_limits()
        return self._sorted_diagnostics()

    def _visit(self, node: Any, pointer: str) -> None:
        if not isinstance(node, dict):
            self._add(
                "INVALID_SCHEMA_NODE",
                pointer,
                "Each schema node must be a JSON object.",
                {"actualType": _json_type_name(node)},
            )
            return

        node_id = id(node)
        if node_id in self._visited_nodes:
            return
        self._visited_nodes.add(node_id)
        self._record_aggregate_data(node, pointer)

        has_type = "type" in node
        types = self._validate_type(node, pointer)
        has_ref = "$ref" in node
        has_any_of = "anyOf" in node
        mode_count = int(has_type) + int(has_ref) + int(has_any_of)
        if mode_count == 0:
            self._add(
                "SCHEMA_TYPE_REQUIRED",
                pointer,
                "A schema node must declare type, anyOf, or $ref.",
            )
        elif mode_count > 1:
            self._add(
                "SCHEMA_COMPOSITION_CONFLICT",
                pointer,
                "A schema node must not combine type, anyOf, and $ref.",
            )

        allowed = self._allowed_keywords(types, has_ref, has_any_of)
        for keyword in node:
            if keyword in UNSUPPORTED_KEYWORDS:
                self._add(
                    "UNSUPPORTED_KEYWORD",
                    pointer,
                    f"Keyword '{keyword}' is not supported by this profile.",
                    {"keyword": keyword},
                )
            elif keyword not in ALL_SUPPORTED_KEYWORDS:
                self._add(
                    "UNKNOWN_KEYWORD",
                    pointer,
                    f"Keyword '{keyword}' is not allowed by this fail-closed profile.",
                    {"keyword": keyword},
                )
            elif keyword not in allowed:
                self._add(
                    "KEYWORD_TYPE_MISMATCH",
                    pointer,
                    f"Keyword '{keyword}' is not valid for this schema node.",
                    {"keyword": keyword},
                )

        self._validate_common_keywords(node, pointer)
        if "object" in types:
            self._validate_object(node, pointer)
        if "array" in types:
            self._validate_array(node, pointer)
        if "string" in types:
            self._validate_string(node, pointer)
        if types & {"number", "integer"}:
            self._validate_number(node, pointer)
        if has_any_of:
            self._validate_any_of(node, pointer)
        if has_ref:
            self._validate_ref_value(node, pointer)
        self._walk_children(node, pointer)

    def _validate_type(self, node: dict[str, Any], pointer: str) -> set[str]:
        if "type" not in node:
            return set()
        raw_type = node["type"]
        if isinstance(raw_type, str):
            if raw_type not in SUPPORTED_TYPES:
                self._add(
                    "TYPE_UNSUPPORTED",
                    pointer,
                    f"Type '{raw_type}' is not supported by this profile.",
                    {"type": raw_type},
                )
                return set()
            return {raw_type}

        if not isinstance(raw_type, list):
            self._add(
                "INVALID_KEYWORD_VALUE",
                pointer,
                "Keyword 'type' must be a string or a nullable two-item array.",
                {"keyword": "type"},
            )
            return set()

        if any(not isinstance(value, str) for value in raw_type):
            valid = False
        else:
            unique = set(raw_type)
            valid = (
                len(raw_type) == 2
                and len(unique) == 2
                and "null" in unique
                and unique <= SUPPORTED_TYPES
            )
        if not valid:
            self._add(
                "INVALID_NULLABLE_TYPE",
                pointer,
                "Array-form type must contain 'null' and one supported non-null type.",
                {"type": raw_type},
            )
            return set()
        return set(raw_type)

    def _allowed_keywords(
        self,
        types: set[str],
        has_ref: bool,
        has_any_of: bool,
    ) -> set[str]:
        if has_ref:
            return {"$ref", "description", "$defs"}
        if has_any_of:
            return {"anyOf", "description", "$defs"}
        allowed = set(COMMON_TYPED_KEYWORDS)
        for schema_type in types:
            allowed.update(TYPE_KEYWORDS.get(schema_type, set()))
        return allowed

    def _validate_common_keywords(
        self, node: dict[str, Any], pointer: str
    ) -> None:
        if "description" in node and not isinstance(node["description"], str):
            self._invalid_value(pointer, "description", "a string")

        if "enum" in node:
            enum = node["enum"]
            if not isinstance(enum, list) or not enum:
                self._invalid_value(pointer, "enum", "a non-empty array")
            elif len({_json_identity(value) for value in enum}) != len(enum):
                self._add(
                    "INVALID_KEYWORD_VALUE",
                    pointer,
                    "Keyword 'enum' must not contain duplicate values.",
                    {"keyword": "enum"},
                )

        if "$defs" in node and not isinstance(node["$defs"], dict):
            self._invalid_value(pointer, "$defs", "an object of schema definitions")

    def _validate_object(self, node: dict[str, Any], pointer: str) -> None:
        properties = node.get("properties")
        required = node.get("required")

        if not isinstance(properties, dict):
            self._add(
                "OBJECT_PROPERTIES_REQUIRED",
                pointer,
                "Object schemas must define 'properties' as an object.",
            )

        required_is_valid = (
            isinstance(required, list)
            and all(isinstance(value, str) for value in required)
            and len(required) == len(set(required))
        )
        if not required_is_valid:
            self._invalid_value(pointer, "required", "an array of unique strings")

        if node.get("additionalProperties") is not False:
            self._add(
                "OBJECT_ADDITIONAL_PROPERTIES_FALSE_REQUIRED",
                pointer,
                "Object schemas must set additionalProperties to false.",
            )

        if isinstance(properties, dict) and required_is_valid:
            property_names = set(properties)
            required_names = set(required)
            missing = sorted(property_names - required_names)
            unexpected = sorted(required_names - property_names)
            if missing or unexpected:
                self._add(
                    "OBJECT_REQUIRED_MISMATCH",
                    pointer,
                    "Object properties and required fields must match.",
                    {
                        "missingRequired": missing,
                        "unexpectedRequired": unexpected,
                    },
                )

    def _validate_array(self, node: dict[str, Any], pointer: str) -> None:
        if not isinstance(node.get("items"), dict):
            self._add(
                "ARRAY_ITEMS_REQUIRED",
                pointer,
                "Array schemas must define 'items' as a schema object.",
            )
        for keyword in ("minItems", "maxItems"):
            if keyword in node and not _is_non_negative_integer(node[keyword]):
                self._invalid_value(pointer, keyword, "a non-negative integer")

    def _validate_string(self, node: dict[str, Any], pointer: str) -> None:
        if "pattern" in node:
            pattern = node["pattern"]
            if not isinstance(pattern, str):
                self._invalid_value(pointer, "pattern", "a string")
            else:
                try:
                    re.compile(pattern)
                except re.error as error:
                    self._add(
                        "INVALID_PATTERN",
                        pointer,
                        "Keyword 'pattern' must contain a valid regular expression.",
                        {"error": str(error)},
                    )

        if "format" in node:
            value = node["format"]
            if not isinstance(value, str) or value not in SUPPORTED_FORMATS:
                self._add(
                    "FORMAT_UNSUPPORTED",
                    pointer,
                    "Keyword 'format' must use a format supported by this profile.",
                    {"format": value},
                )

    def _validate_number(self, node: dict[str, Any], pointer: str) -> None:
        keywords = TYPE_KEYWORDS["number"]
        for keyword in sorted(keywords):
            if keyword not in node:
                continue
            value = node[keyword]
            if not _is_json_number(value):
                self._invalid_value(pointer, keyword, "a finite JSON number")
            elif keyword == "multipleOf" and value <= 0:
                self._invalid_value(pointer, keyword, "a number greater than zero")

    def _validate_any_of(self, node: dict[str, Any], pointer: str) -> None:
        value = node.get("anyOf")
        if not isinstance(value, list) or not value:
            self._invalid_value(pointer, "anyOf", "a non-empty array of schemas")

    def _validate_ref_value(self, node: dict[str, Any], pointer: str) -> None:
        value = node.get("$ref")
        if not isinstance(value, str) or not value:
            self._invalid_value(pointer, "$ref", "a non-empty string")

    def _walk_children(self, node: dict[str, Any], pointer: str) -> None:
        properties = node.get("properties")
        if isinstance(properties, dict):
            for name, child in properties.items():
                self._visit(child, _pointer_join(pointer, "properties", name))

        items = node.get("items")
        if "items" in node:
            self._visit(items, _pointer_join(pointer, "items"))

        any_of = node.get("anyOf")
        if isinstance(any_of, list):
            for index, child in enumerate(any_of):
                self._visit(child, _pointer_join(pointer, "anyOf", str(index)))

        definitions = node.get("$defs")
        if isinstance(definitions, dict):
            for name, child in definitions.items():
                if isinstance(child, dict) and id(child) not in self._definition_ids:
                    self._definition_entries.append(child)
                    self._definition_ids.add(id(child))
                self._visit(child, _pointer_join(pointer, "$defs", name))

    def _record_aggregate_data(
        self, node: dict[str, Any], pointer: str
    ) -> None:
        properties = node.get("properties")
        if isinstance(properties, dict):
            self._property_count += len(properties)
            self._total_string_length += sum(len(name) for name in properties)

        definitions = node.get("$defs")
        if isinstance(definitions, dict):
            self._total_string_length += sum(len(name) for name in definitions)

        enum = node.get("enum")
        if isinstance(enum, list):
            self._enum_value_count += len(enum)
            string_length = sum(len(value) for value in enum if isinstance(value, str))
            self._total_string_length += string_length
            if (
                len(enum) > LARGE_ENUM_THRESHOLD
                and string_length > MAX_LARGE_ENUM_STRING_LENGTH
            ):
                self._add(
                    "ENUM_STRING_LENGTH_EXCEEDED",
                    pointer,
                    "A large enum exceeds the total string-length limit.",
                    {
                        "actual": string_length,
                        "maximum": MAX_LARGE_ENUM_STRING_LENGTH,
                        "enumValues": len(enum),
                    },
                )

        const = node.get("const")
        if isinstance(const, str):
            self._total_string_length += len(const)

        if "$ref" in node:
            self._references.append((pointer, node["$ref"]))

    def _validate_references(self) -> None:
        for pointer, reference in self._references:
            if not isinstance(reference, str) or not reference:
                continue
            target, reason, is_external = self._resolve_reference(reference)
            if target is not None:
                continue
            code = (
                "EXTERNAL_REFERENCE_UNSUPPORTED"
                if is_external
                else "INVALID_REFERENCE"
            )
            self._add(
                code,
                pointer,
                reason or "The reference is invalid.",
                {"reference": reference},
            )

    def _resolve_reference(
        self, reference: str
    ) -> tuple[dict[str, Any] | None, str | None, bool]:
        if not reference.startswith("#"):
            return None, "Only local document references are supported.", True
        if reference == "#":
            if isinstance(self.document, dict):
                return self.document, None, False
            return None, "The document root is not a schema object.", False
        if not reference.startswith("#/"):
            return None, "Only '#' and JSON Pointer fragments are supported.", False

        fragment = reference[1:]
        if re.search(r"%(?![0-9A-Fa-f]{2})", fragment):
            return None, "The reference contains invalid percent encoding.", False
        try:
            decoded = unquote_to_bytes(fragment).decode("utf-8")
        except UnicodeDecodeError:
            return None, "The reference contains invalid UTF-8 encoding.", False
        current: Any = self.document
        for raw_token in decoded[1:].split("/"):
            if re.search(r"~(?![01])", raw_token):
                return None, "The reference contains an invalid JSON Pointer escape.", False
            token = raw_token.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and token in current:
                current = current[token]
            elif isinstance(current, list):
                if not token.isdigit() or (
                    len(token) > 1 and token.startswith("0")
                ):
                    return None, "The reference contains an invalid array index.", False
                index = int(token)
                if index >= len(current):
                    return None, "The reference points outside an array.", False
                current = current[index]
            else:
                return None, "The reference target does not exist.", False
        if not isinstance(current, dict):
            return None, "The reference target is not a schema object.", False
        return current, None, False

    def _validate_limits(self) -> None:
        if self._property_count > MAX_PROPERTIES:
            self._add(
                "PROPERTY_LIMIT_EXCEEDED",
                "/",
                "The schema exceeds the total object-property limit.",
                {"actual": self._property_count, "maximum": MAX_PROPERTIES},
            )
        if self._total_string_length > MAX_TOTAL_STRING_LENGTH:
            self._add(
                "STRING_LENGTH_LIMIT_EXCEEDED",
                "/",
                "The schema exceeds the total counted string-length limit.",
                {
                    "actual": self._total_string_length,
                    "maximum": MAX_TOTAL_STRING_LENGTH,
                },
            )
        if self._enum_value_count > MAX_ENUM_VALUES:
            self._add(
                "ENUM_VALUE_LIMIT_EXCEEDED",
                "/",
                "The schema exceeds the total enum-value limit.",
                {"actual": self._enum_value_count, "maximum": MAX_ENUM_VALUES},
            )

        maximum_depth = self._effective_object_depth()
        if maximum_depth > MAX_OBJECT_DEPTH:
            self._add(
                "OBJECT_DEPTH_LIMIT_EXCEEDED",
                "/",
                "The schema exceeds the effective object-nesting limit.",
                {"actual": maximum_depth, "maximum": MAX_OBJECT_DEPTH},
            )

    def _effective_object_depth(self) -> int:
        entries: list[dict[str, Any]] = []
        if isinstance(self.document, dict):
            entries.append(self.document)
        entries.extend(self._definition_entries)
        return max(
            (self._depth_from(entry, 0, frozenset()) for entry in entries),
            default=0,
        )

    def _depth_from(
        self,
        node: Any,
        current_depth: int,
        active: frozenset[int],
    ) -> int:
        if not isinstance(node, dict) or id(node) in active:
            return current_depth
        active = active | {id(node)}
        raw_types = _raw_valid_types(node.get("type"))
        next_depth = current_depth + int("object" in raw_types)
        maximum = next_depth

        reference = node.get("$ref")
        if isinstance(reference, str):
            target, _, _ = self._resolve_reference(reference)
            if target is not None:
                maximum = max(
                    maximum,
                    self._depth_from(target, next_depth, active),
                )

        properties = node.get("properties")
        if isinstance(properties, dict):
            for child in properties.values():
                maximum = max(
                    maximum,
                    self._depth_from(child, next_depth, active),
                )
        if isinstance(node.get("items"), dict):
            maximum = max(
                maximum,
                self._depth_from(node["items"], next_depth, active),
            )
        if isinstance(node.get("anyOf"), list):
            for child in node["anyOf"]:
                maximum = max(
                    maximum,
                    self._depth_from(child, next_depth, active),
                )
        return maximum

    def _invalid_value(
        self,
        pointer: str,
        keyword: str,
        expectation: str,
    ) -> None:
        self._add(
            "INVALID_KEYWORD_VALUE",
            pointer,
            f"Keyword '{keyword}' must be {expectation}.",
            {"keyword": keyword},
        )

    def _add(
        self,
        code: str,
        pointer: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.diagnostics.append(
            Diagnostic(code, pointer, message, details or {})
        )

    def _sorted_diagnostics(self) -> list[Diagnostic]:
        unique: dict[tuple[str, str, str, str], Diagnostic] = {}
        for diagnostic in self.diagnostics:
            details_key = json.dumps(
                diagnostic.details,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            key = (
                diagnostic.schema_pointer,
                diagnostic.code,
                diagnostic.message,
                details_key,
            )
            unique[key] = diagnostic
        return [unique[key] for key in sorted(unique)]


def _pointer_join(base: str, *tokens: str) -> str:
    prefix = "" if base == "/" else base
    encoded = [token.replace("~", "~0").replace("/", "~1") for token in tokens]
    return prefix + "/" + "/".join(encoded)


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _json_identity(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, float)):
        return ("number", Decimal(str(value)))
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_json_identity(item) for item in value))
    if isinstance(value, dict):
        return (
            "object",
            tuple(
                (key, _json_identity(item))
                for key, item in sorted(value.items())
            ),
        )
    raise TypeError(f"Unexpected decoded JSON value: {type(value).__name__}")


def _is_json_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
    )


def _is_non_negative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _raw_valid_types(value: Any) -> set[str]:
    if isinstance(value, str) and value in SUPPORTED_TYPES:
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value) & SUPPORTED_TYPES
    return set()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise InvalidConstantError(f"Invalid JSON numeric constant: {value}")


def _parse_document(raw: bytes) -> tuple[Any | None, Diagnostic | None]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return None, Diagnostic(
            "INVALID_UTF8",
            "/",
            "The schema file must be valid UTF-8.",
            {"byteOffset": error.start},
        )

    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        return None, Diagnostic(
            "INVALID_JSON",
            "/",
            "The schema file must contain valid JSON.",
            {"line": error.lineno, "column": error.colno, "error": error.msg},
        )
    except (DuplicateKeyError, InvalidConstantError) as error:
        return None, Diagnostic(
            "INVALID_JSON",
            "/",
            "The schema file must contain strict JSON.",
            {"error": str(error)},
        )
    return document, None


def _result(
    path: str,
    diagnostics: list[Diagnostic],
) -> dict[str, Any]:
    return {
        "profile": PROFILE,
        "path": path,
        "valid": not diagnostics,
        "errors": [diagnostic.as_dict() for diagnostic in diagnostics],
    }


def _print_result(
    path: str,
    diagnostics: list[Diagnostic],
    output_format: str,
) -> None:
    if output_format == "json":
        print(json.dumps(_result(path, diagnostics), ensure_ascii=False, indent=2))
        return
    if not diagnostics:
        print(f"OK: {path} ({PROFILE})")
        return
    for diagnostic in diagnostics:
        print(
            f"{path}:{diagnostic.schema_pointer}: "
            f"{diagnostic.code}: {diagnostic.message}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a JSON Schema for OpenAI Structured Outputs."
    )
    parser.add_argument(
        "--profile",
        choices=(PROFILE,),
        default=PROFILE,
        help=f"validation profile (default: {PROFILE})",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="diagnostic output format (default: text)",
    )
    parser.add_argument("schema_path", help="path to one UTF-8 JSON Schema file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path = Path(args.schema_path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        print(f"Error: cannot read schema file '{args.schema_path}': {error}", file=sys.stderr)
        return 2

    document, parse_diagnostic = _parse_document(raw)
    if parse_diagnostic is not None:
        diagnostics = [parse_diagnostic]
    else:
        diagnostics = SchemaValidator(document).validate()
    _print_result(args.schema_path, diagnostics, args.output_format)
    return 1 if diagnostics else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(2) from None
    except Exception as error:  # Defensive boundary for a CI-facing command.
        print(f"Internal error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
