from __future__ import annotations

from typing import Any


def get_nested(
    source: dict[str, Any],
    dotted_path: str,
    default: Any = "",
) -> Any:
    current: Any = source
    for token in dotted_path.split("."):
        if not isinstance(current, dict) or token not in current:
            return default
        current = current[token]
    return current


def map_to_pdf_fields(
    data: dict[str, Any],
    mapping: dict[str, str],
) -> dict[str, str]:
    output: dict[str, str] = {}
    for pdf_field, source_path in mapping.items():
        value = get_nested(data, source_path, "")
        if isinstance(value, list):
            output[pdf_field] = ", ".join(str(v) for v in value)
        else:
            output[pdf_field] = str(value)
    return output
