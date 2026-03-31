from __future__ import annotations

import json
from typing import Any

from fireform.models import ExtractionResult

SYSTEM_PROMPT = """You are a fire incident data extractor.
Extract structured data from incident descriptions and return ONLY valid JSON.
No markdown, no preamble, no explanations.
You MUST provide confidence scores for fields: `nc:ActivityDate`, `em:IncidentCategoryCode` as part of your output based on schema if required. If not required by schema, you can still add them if you want.
The JSON must match this schema exactly:
{schema}

Examples:
Input: "Respond to structure fire at 123 Main St at 14:00."
Output: {{"nc:IncidentID": "UNKNOWN", "nc:ActivityDate": "UNKNOWN", "nc:ActivityTime": "14:00", "nc:Location": {{"nc:Address": "123 Main St", "nc:City": "UNKNOWN", "nc:State": "UNKNOWN"}}, "em:IncidentCategoryCode": "STRUCTURE_FIRE", "nc:SystemUnit": ["UNKNOWN"], "nc:Casualties": {{"nc:Injuries": 0, "nc:Fatalities": 0}}, "nc:PropertyDamage": "UNKNOWN", "nc:ActivityDescription": "Structure fire"}}
"""

REPAIR_PROMPT = """The previous JSON output failed validation.
Errors:
{validation_errors}

Previous JSON output:
{previous_json}

Schema:
{schema}

Fix the JSON to conform to the schema and return ONLY valid JSON.
"""

def _ollama_chat(
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    format: str = "json" # type: ignore # type: ignore
) -> str:
    try:
        import ollama
    except ImportError as exc:
        raise RuntimeError("ollama package is not installed.") from exc

    response = ollama.chat(
        model=model,
        messages=messages,
        format=format, # type: ignore # type: ignore
        options={"temperature": temperature}, # type: ignore # type: ignore
    )
    try:
        return response["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Unexpected Ollama response shape.") from exc


def _detect_hallucinations(original_text: str, extracted: dict[str, Any]) -> list[str]:
    """Flag fields where the LLM invented data not present in original input."""
    suspicious = []
    text_lower = original_text.lower()
    
    def walk_dict(d, prefix=""):
        for k, v in d.items():
            if isinstance(v, dict):
                walk_dict(v, f"{prefix}{k}.")
            elif isinstance(v, str):
                if v != "UNKNOWN" and v.lower() not in text_lower:
                    suspicious.append(f"{prefix}{k}")
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item != "UNKNOWN" and item.lower() not in text_lower:
                        suspicious.append(f"{prefix}{k}")
    
    walk_dict(extracted)
    return suspicious


def extract_incident_data(
    text: str,
    *,
    model: str = "llama3.1",
    schema: dict[str, Any] | None = None,
    temperature: float = 0.0,
) -> ExtractionResult:
    schema = schema or {}
    
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(schema=json.dumps(schema)),
        },
        {"role": "user", "content": text},
    ]

    try:
        raw = _ollama_chat(model, messages, temperature)
    except Exception as exc:
        return ExtractionResult(data=None, attempts=1, error=str(exc))

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ExtractionResult(data=None, attempts=1, error=f"Failed to parse JSON: {exc.msg}", raw_response=raw)

    hallucinations = _detect_hallucinations(text, data)
    data["_hallucinations"] = hallucinations
    
    return ExtractionResult(data=data, attempts=1, raw_response=raw)


def repair_extracted_data(
    previous_json: dict[str, Any],
    schema: dict[str, Any],
    validation_errors: list[str],
    *,
    model: str = "llama3.1",
    temperature: float = 0.0,
) -> ExtractionResult:
    
    messages = [
        {
            "role": "system",
            "content": REPAIR_PROMPT.format(
                schema=json.dumps(schema),
                validation_errors=json.dumps(validation_errors),
                previous_json=json.dumps(previous_json),
            ),
        },
    ]

    try:
        raw = _ollama_chat(model, messages, temperature)
    except Exception as exc:
        return ExtractionResult(data=None, attempts=1, error=str(exc))

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ExtractionResult(data=None, attempts=1, error=f"Model repair returned invalid JSON: {exc.msg}", raw_response=raw)

    return ExtractionResult(data=data, attempts=1, raw_response=raw)
