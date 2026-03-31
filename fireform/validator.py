# pyright: reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from jsonschema import (  # type: ignore[import-untyped]
    Draft202012Validator,
    FormatChecker,
)


def _semantic_checks(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    casualties = data.get("nc:Casualties", {})
    for key in ("nc:Injuries", "nc:Fatalities"):
        value = casualties.get(key)
        if value is not None and value < 0:
            errors.append(f"nc:Casualties.{key} must be >= 0")

    units = data.get("em:UnitsDispatched", [])
    if isinstance(units, list) and len(units) == 0:
        errors.append(
            "em:UnitsDispatched should include at least one responding unit"
        )

    return errors


def validate_incident_data(
    data: dict[str, Any],
    schema: dict[str, Any],
) -> tuple[bool, list[str]]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(
        validator.iter_errors(data),
        key=lambda err: err.path,
    )

    messages = [err.message for err in schema_errors]
    messages.extend(_semantic_checks(data))

    return len(messages) == 0, messages
