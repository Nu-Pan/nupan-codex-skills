from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "dist" / "scripts" / "validate_schema.py"
PROFILE = "openai-structured-outputs-2026-08"


def object_schema(properties: dict[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def run_file(
    path: Path,
    *,
    output_format: str = "json",
    extra_arguments: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--format",
            output_format,
            *extra_arguments,
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def run_schema(
    tmp_path: Path,
    schema: object,
    *,
    output_format: str = "json",
) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    return run_file(path, output_format=output_format)


def error_codes(result: subprocess.CompletedProcess[str]) -> set[str]:
    return {error["code"] for error in json.loads(result.stdout)["errors"]}


def test_accepts_supported_nested_definitions_and_recursion(tmp_path: Path) -> None:
    schema = object_schema(
        {
            "email": {
                "type": "string",
                "pattern": r"^[^@]+@[^@]+$",
                "format": "email",
            },
            "temperature": {
                "type": ["number", "null"],
                "minimum": -130,
                "maximum": 130,
                "multipleOf": 0.5,
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 5,
            },
            "choice": {
                "anyOf": [
                    {"type": "string", "const": "auto"},
                    {"type": "integer", "enum": [1, 2]},
                ]
            },
            "node": {"$ref": "#/$defs/a~1b~0c"},
        }
    )
    schema["$defs"] = {
        "a/b~c": object_schema(
            {
                "value": {"type": "integer"},
                "next": {
                    "anyOf": [
                        {"$ref": "#/$defs/a~1b~0c"},
                        {"type": "null"},
                    ]
                },
            }
        )
    }

    result = run_schema(tmp_path, schema)

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "profile": PROFILE,
        "path": str(tmp_path / "schema.json"),
        "valid": True,
        "errors": [],
    }


def test_text_output_reports_success_and_diagnostics(tmp_path: Path) -> None:
    valid_result = run_schema(
        tmp_path,
        object_schema({"answer": {"type": "string"}}),
        output_format="text",
    )
    assert valid_result.returncode == 0
    assert len(valid_result.stdout.splitlines()) == 1
    assert str(tmp_path / "schema.json") in valid_result.stdout
    assert PROFILE in valid_result.stdout

    invalid_result = run_schema(
        tmp_path,
        object_schema({"answer": {"type": "string", "title": "Answer"}}),
        output_format="text",
    )
    assert invalid_result.returncode == 1
    assert "UNKNOWN_KEYWORD" in invalid_result.stdout
    assert "/properties/answer" in invalid_result.stdout


def test_reports_required_mismatch_with_fixed_json_shape(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "status": {"type": "string"},
        },
        "required": ["answer", "obsolete"],
        "additionalProperties": False,
    }

    result = run_schema(tmp_path, schema)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert set(payload) == {"profile", "path", "valid", "errors"}
    assert len(payload["errors"]) == 1
    error = payload["errors"][0]
    assert set(error) == {"code", "schemaPointer", "message", "details"}
    assert error["code"] == "OBJECT_REQUIRED_MISMATCH"
    assert error["schemaPointer"] == "/"
    assert isinstance(error["message"], str) and error["message"].strip()
    assert error["details"] == {
        "missingRequired": ["status"],
        "unexpectedRequired": ["obsolete"],
    }


def test_rejects_root_object_and_keyword_violations(tmp_path: Path) -> None:
    schema = {
        "type": "string",
        "anyOf": [{"type": "string"}],
        "allOf": [{"type": "string"}],
        "mystery": True,
    }

    result = run_schema(tmp_path, schema)

    assert result.returncode == 1
    assert {
        "ROOT_OBJECT_REQUIRED",
        "ROOT_ANY_OF_FORBIDDEN",
        "SCHEMA_COMPOSITION_CONFLICT",
        "UNSUPPORTED_KEYWORD",
        "UNKNOWN_KEYWORD",
    } <= error_codes(result)


def test_requires_additional_properties_false_for_every_object(
    tmp_path: Path,
) -> None:
    schema = object_schema(
        {
            "nested": {
                "type": "object",
                "properties": {},
                "required": [],
            }
        }
    )

    result = run_schema(tmp_path, schema)

    assert result.returncode == 1
    assert "OBJECT_ADDITIONAL_PROPERTIES_FALSE_REQUIRED" in error_codes(result)


@pytest.mark.parametrize(
    ("property_schema", "expected_code"),
    [
        ({"type": ["string", "integer"]}, "INVALID_NULLABLE_TYPE"),
        ({"type": "array"}, "ARRAY_ITEMS_REQUIRED"),
        ({"type": "string", "pattern": "["}, "INVALID_PATTERN"),
        ({"type": "string", "format": "uri"}, "FORMAT_UNSUPPORTED"),
        ({"type": "number", "multipleOf": 0}, "INVALID_KEYWORD_VALUE"),
        ({"type": "string", "properties": {}}, "KEYWORD_TYPE_MISMATCH"),
        (True, "INVALID_SCHEMA_NODE"),
    ],
)
def test_rejects_invalid_schema_nodes(
    tmp_path: Path,
    property_schema: object,
    expected_code: str,
) -> None:
    result = run_schema(tmp_path, object_schema({"value": property_schema}))

    assert result.returncode == 1
    assert expected_code in error_codes(result)


@pytest.mark.parametrize(
    ("reference", "expected_code"),
    [
        ("https://example.com/schema.json", "EXTERNAL_REFERENCE_UNSUPPORTED"),
        ("#/$defs/missing", "INVALID_REFERENCE"),
        ("#bad-anchor", "INVALID_REFERENCE"),
        ("#/$defs/value", "INVALID_REFERENCE"),
        ("#/$defs/%FF", "INVALID_REFERENCE"),
    ],
)
def test_rejects_invalid_references(
    tmp_path: Path,
    reference: str,
    expected_code: str,
) -> None:
    schema = object_schema({"value": {"$ref": reference}})
    schema["$defs"] = {"value": "not-a-schema"}

    result = run_schema(tmp_path, schema)

    assert result.returncode == 1
    assert expected_code in error_codes(result)


@pytest.mark.parametrize("index", ["01", "١", "²", "-", "9" * 5_000])
def test_rejects_non_canonical_or_out_of_range_json_pointer_array_index(
    tmp_path: Path, index: str,
) -> None:
    choice = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
    schema = object_schema(
        {
            "choice": choice,
            "copy": {"$ref": f"#/properties/choice/anyOf/{index}"},
        }
    )

    result = run_schema(tmp_path, schema)

    assert result.returncode == 1
    assert "INVALID_REFERENCE" in error_codes(result)


def test_counts_each_physical_schema_node_once_when_referenced(
    tmp_path: Path,
) -> None:
    schema = object_schema(
        {
            "first": {"$ref": "#/$defs/shared"},
            "second": {"$ref": "#/$defs/shared"},
        }
    )
    schema["$defs"] = {
        "shared": object_schema(
            {f"p{index}": {"type": "string"} for index in range(4_998)}
        )
    }

    result = run_schema(tmp_path, schema)

    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("reference", "payload", "expected_pointer", "expected_code"),
    [
        ("#/properties", {}, "/properties", "SCHEMA_TYPE_REQUIRED"),
        ("#/const", {"type": "invalid"}, "/const", "TYPE_UNSUPPORTED"),
        (
            "#/const/a~1b~0c",
            {"a/b~c": {"type": "string", "unknown": True}},
            "/const/a~1b~0c",
            "UNKNOWN_KEYWORD",
        ),
        (
            "#/const/%E5%90%8D%E5%89%8D",
            {"名前": {"type": "array"}},
            "/const/名前",
            "ARRAY_ITEMS_REQUIRED",
        ),
    ],
)
def test_validates_referenced_objects_at_their_document_location(
    tmp_path: Path,
    reference: str,
    payload: object,
    expected_pointer: str,
    expected_code: str,
) -> None:
    schema = object_schema({"value": {"$ref": reference}})
    schema["const"] = payload

    result = run_schema(tmp_path, schema)

    assert result.returncode == 1
    assert any(
        error["code"] == expected_code and error["schemaPointer"] == expected_pointer
        for error in json.loads(result.stdout)["errors"]
    )


def test_validates_transitive_references_and_stops_cycles(tmp_path: Path) -> None:
    schema = object_schema({"value": {"$ref": "#/const/first"}})
    schema["const"] = {
        "first": object_schema({
            "next": {"$ref": "#/const/second"},
            "invalid": {"type": "string", "unknown": True},
        }),
        "second": {"$ref": "#/const/first"},
    }

    result = run_schema(tmp_path, schema)

    assert result.returncode == 1
    errors = json.loads(result.stdout)["errors"]
    assert [(e["code"], e["schemaPointer"]) for e in errors] == [
        ("UNKNOWN_KEYWORD", "/const/first/properties/invalid")
    ]


@pytest.mark.parametrize("extra_property", [False, True])
def test_counts_shared_reference_targets_outside_schema_keywords_once(
    tmp_path: Path, extra_property: bool
) -> None:
    schema = object_schema({
        "first": {"$ref": "#/const"},
        "second": {"$ref": "#/const"},
    })
    schema["const"] = object_schema({
        f"p{index}": {"type": "string"}
        for index in range(4_998 + int(extra_property))
    })

    result = run_schema(tmp_path, schema)

    assert result.returncode == int(extra_property), result.stdout
    assert error_codes(result) == ({"PROPERTY_LIMIT_EXCEEDED"} if extra_property else set())


def test_does_not_validate_unreferenced_const_as_a_schema(tmp_path: Path) -> None:
    schema = object_schema({})
    schema["const"] = {"type": "invalid", "unknown": True}

    result = run_schema(tmp_path, schema)

    assert result.returncode == 0, result.stdout


def test_enum_duplicate_detection_uses_json_numeric_equality(
    tmp_path: Path,
) -> None:
    result = run_schema(
        tmp_path,
        object_schema({"value": {"type": "number", "enum": [1, 1.0]}}),
    )

    assert result.returncode == 1
    assert "INVALID_KEYWORD_VALUE" in error_codes(result)


@pytest.mark.parametrize(
    ("numbers", "duplicate"),
    [
        ("1,1.0", True),
        ("1e400,10e399", True),
        ("9007199254740992.0,9007199254740993.0", False),
        ("1e400,2e400", False),
        ("1e-400,2e-400", False),
    ],
)
def test_compares_enum_numbers_without_rounding(
    tmp_path: Path, numbers: str, duplicate: bool
) -> None:
    path = tmp_path / "schema.json"
    path.write_text(
        '{"type":"object","properties":{"n":{"type":"number","enum":['
        + numbers + ']}},"required":["n"],"additionalProperties":false}',
        encoding="utf-8",
    )
    result = run_file(path)
    assert result.returncode == int(duplicate), result.stderr
    assert error_codes(result) == ({"INVALID_KEYWORD_VALUE"} if duplicate else set())


@pytest.mark.parametrize("keyword", ["minItems", "maxItems"])
@pytest.mark.parametrize(
    ("number", "valid"),
    [("0.0", True), ("1e400", True), ("1.0000000000000000001", False), ("1e-400", False)],
)
def test_array_bounds_use_integer_values_not_number_spelling(
    tmp_path: Path, keyword: str, number: str, valid: bool
) -> None:
    path = tmp_path / "schema.json"
    path.write_text(
        '{"type":"object","properties":{"values":{"type":"array",'
        '"items":{"type":"string"},"' + keyword + '":' + number
        + '}},"required":["values"],"additionalProperties":false}',
        encoding="utf-8",
    )
    result = run_file(path)
    assert result.returncode == int(not valid), result.stderr
    assert error_codes(result) == (set() if valid else {"INVALID_KEYWORD_VALUE"})


def test_retains_decimal_values_in_validation_and_json_diagnostics(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text(
        '{"type":"object","properties":{'
        '"n":{"type":"number","multipleOf":1e-400,"maximum":1e400},'
        '"s":{"type":"string","format":9007199254740993.25}},'
        '"required":["n","s"],"additionalProperties":false}',
        encoding="utf-8",
    )
    result = run_file(path)
    payload = json.loads(result.stdout, parse_float=Decimal)
    assert result.returncode == 1, result.stderr
    assert error_codes(result) == {"FORMAT_UNSUPPORTED"}
    assert payload["errors"][0]["details"]["format"] == Decimal("9007199254740993.25")
    assert "Infinity" not in result.stdout


@pytest.mark.parametrize("index", ["0", "1"])
def test_accepts_canonical_array_references(tmp_path: Path, index: str) -> None:
    result = run_schema(tmp_path, object_schema({
        "choice": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        "copy": {"$ref": f"#/properties/choice/anyOf/{index}"},
    }))
    assert result.returncode == 0, result.stdout


def test_completes_validation_of_repeated_acyclic_references(tmp_path: Path) -> None:
    # A small document represents many paths through shared definitions.
    # The subprocess timeout detects failure to finish, not a timing threshold.
    schema = object_schema({"value": {"$ref": "#/$defs/n0"}})
    schema["$defs"] = {
        f"n{index}": {"anyOf": [
            {"$ref": f"#/$defs/n{index + 1}"},
            {"$ref": f"#/$defs/n{index + 1}"},
        ]} for index in range(30)
    }
    schema["$defs"]["n30"] = {"type": "string"}
    result = run_schema(tmp_path, schema)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("first", "last", "depth", "too_deep"),
    [
        ("shared", "shared", 8, False),
        ("shared", "shared", 9, True),
        ("a", "b", 7, False),
        ("a", "b", 8, True),
    ],
)
def test_shared_and_recursive_references_preserve_depth_in_each_parent(
    tmp_path: Path, first: str, last: str, depth: int, too_deep: bool
) -> None:
    schema = object_schema({
        "short": {"$ref": f"#/$defs/{first}"},
        "long": nested_objects(depth),
    })
    leaf = schema["properties"]["long"]
    while leaf["properties"]:
        leaf = leaf["properties"]["child"]
    leaf["properties"]["next"] = {"$ref": f"#/$defs/{last}"}
    leaf["required"] = ["next"]
    schema["$defs"] = {
        "shared": object_schema({"value": {"type": "string"}}),
        "a": object_schema({"next": {"$ref": "#/$defs/b"}}),
        "b": object_schema({"next": {"$ref": "#/$defs/a"}}),
    }
    result = run_schema(tmp_path, schema)
    assert result.returncode == int(too_deep), result.stdout
    assert error_codes(result) == ({"OBJECT_DEPTH_LIMIT_EXCEEDED"} if too_deep else set())


def test_installed_cli_runs_with_only_standard_library(tmp_path: Path) -> None:
    repository = SKILL_ROOT.parents[1]
    target = tmp_path / "installed"
    target.mkdir()
    installed = subprocess.run(
        [sys.executable, str(repository / "scripts/install_skill.py"), SKILL_ROOT.name, str(target)],
        check=False, capture_output=True, text=True, timeout=10,
    )
    assert installed.returncode == 0, installed.stderr
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(object_schema({"answer": {"type": "string"}})), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(target / ".agents/skills" / SKILL_ROOT.name / "scripts/validate_schema.py"), "--format", "json", str(path)],
        cwd=target, check=False, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["valid"] is True


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    [
        (b'{"type": "object"', "INVALID_JSON"),
        (b'{"type":"object","type":"string"}', "INVALID_JSON"),
        (b'{"type":"object","const":NaN}', "INVALID_JSON"),
        (b"\xff", "INVALID_UTF8"),
    ],
)
def test_rejects_invalid_json_documents(
    tmp_path: Path,
    raw: bytes,
    expected_code: str,
) -> None:
    path = tmp_path / "schema.json"
    path.write_bytes(raw)

    result = run_file(path)

    assert result.returncode == 1
    assert error_codes(result) == {expected_code}


def test_uses_exit_two_for_usage_and_file_errors(tmp_path: Path) -> None:
    missing = run_file(tmp_path / "missing.json")
    assert missing.returncode == 2
    assert "cannot read schema file" in missing.stderr

    path = tmp_path / "schema.json"
    path.write_text(json.dumps(object_schema({})), encoding="utf-8")
    bad_profile = run_file(
        path,
        extra_arguments=("--profile", "future-profile"),
    )
    assert bad_profile.returncode == 2
    assert "invalid choice" in bad_profile.stderr


def test_diagnostics_have_deterministic_order(tmp_path: Path) -> None:
    schema = object_schema(
        {
            "z": {"type": "string", "title": "Z", "format": "uri"},
            "a": {"type": "string", "title": "A", "format": "uri"},
        }
    )

    first = run_schema(tmp_path, schema)
    second = run_schema(tmp_path, schema)
    first_payload = json.loads(first.stdout)

    assert first.stdout == second.stdout
    keys = [
        (
            error["schemaPointer"],
            error["code"],
            error["message"],
            json.dumps(error["details"], sort_keys=True),
        )
        for error in first_payload["errors"]
    ]
    assert keys == sorted(keys)


def nested_objects(depth: int) -> dict[str, object]:
    schema: dict[str, object] = object_schema({})
    for _ in range(depth - 1):
        schema = object_schema({"child": schema})
    return schema


def large_string_enum(total_length: int) -> list[str]:
    values = [f"v{index:03d}" for index in range(251)]
    remaining = total_length - sum(len(value) for value in values)
    assert remaining >= 0
    values[0] += "x" * remaining
    return values


@pytest.mark.parametrize(
    ("schema", "expected_code"),
    [
        (
            object_schema(
                {f"p{index}": {"type": "string"} for index in range(5_000)}
            ),
            None,
        ),
        (
            object_schema(
                {f"p{index}": {"type": "string"} for index in range(5_001)}
            ),
            "PROPERTY_LIMIT_EXCEEDED",
        ),
        (nested_objects(10), None),
        (nested_objects(11), "OBJECT_DEPTH_LIMIT_EXCEEDED"),
        (object_schema({"x" * 120_000: {"type": "string"}}), None),
        (
            object_schema({"x" * 120_001: {"type": "string"}}),
            "STRING_LENGTH_LIMIT_EXCEEDED",
        ),
        (
            object_schema({"value": {"type": "integer", "enum": list(range(1_000))}}),
            None,
        ),
        (
            object_schema({"value": {"type": "integer", "enum": list(range(1_001))}}),
            "ENUM_VALUE_LIMIT_EXCEEDED",
        ),
        (
            object_schema(
                {"value": {"type": "string", "enum": large_string_enum(15_000)}}
            ),
            None,
        ),
        (
            object_schema(
                {"value": {"type": "string", "enum": large_string_enum(15_001)}}
            ),
            "ENUM_STRING_LENGTH_EXCEEDED",
        ),
    ],
)
def test_enforces_documented_limit_boundaries(
    tmp_path: Path,
    schema: dict[str, object],
    expected_code: str | None,
) -> None:
    result = run_schema(tmp_path, schema)

    if expected_code is None:
        assert result.returncode == 0, result.stdout
        assert json.loads(result.stdout)["errors"] == []
    else:
        assert result.returncode == 1
        assert expected_code in error_codes(result)
