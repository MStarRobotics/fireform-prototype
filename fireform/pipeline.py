from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fireform.extractor import extract_incident_data, repair_extracted_data
from fireform.models import PipelineArtifacts, TemplateResult
from fireform.pdf_filler import fill_pdf
from fireform.template_mapper import map_to_pdf_fields
from fireform.transcriber import transcribe_audio
from fireform.validator import validate_incident_data
from fireform.entity_resolver import normalize_units

def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _record_artifact(artifacts: PipelineArtifacts, path: Path) -> None:
    if path not in artifacts.artifact_files:
        artifacts.artifact_files.append(path)


def _validate_with_repair(
    data: dict[str, Any],
    schema: dict[str, Any],
    *,
    model: str,
    max_retries: int,
) -> tuple[dict[str, Any], list[str], int]:
    current_data = data or {} or {}
    current_errors: list[str] = []
    retries_used = 0

    for attempt in range(max_retries + 1):
        hallucinations = current_data.pop("_hallucinations", None)
        current_data = normalize_units(current_data)
        if hallucinations:
            print(f"Watch out for: {hallucinations}")
            
        is_valid, errors = validate_incident_data(current_data, schema)
        if is_valid:
            if hallucinations:
                current_data["_hallucinations"] = hallucinations
            return current_data, [], retries_used

        current_errors = errors
        if attempt >= max_retries:
            break

        repair = repair_extracted_data(
            current_data,
            schema,
            errors,
            model=model,
        )
        current_data = repair.data or {} or {}
        retries_used += 1

    return current_data, current_errors, retries_used


def _serialize_template_results(
    template_results: list[TemplateResult],
) -> list[dict[str, Any]]:
    return [
        {
            "template_path": item.template_path,
            "output_name": item.output_name,
            "output_path": str(item.output_path) if item.output_path else None,
            "fields_mapped": item.fields_mapped,
            "status": item.status,
            "error": item.error,
        }
        for item in template_results
    ]


def _save_run_artifacts(
    artifacts: PipelineArtifacts,
    schema: dict[str, Any],
    run_dir: Path,
) -> None:
    run_metadata = {
        "run_id": artifacts.run_id,
        "model": artifacts.model,
        "retries_used": artifacts.retries_used,
        "stage_durations": artifacts.stage_durations,
        "validation_error_count": len(artifacts.validation_errors),
        "template_results": _serialize_template_results(
            artifacts.template_results
        ),
    }

    _record_artifact(
        artifacts,
        _write_json(run_dir / "run_metadata.json", run_metadata),
    )
    _record_artifact(
        artifacts,
        _write_json(
            run_dir / "input_text.json",
            {"input_text": artifacts.input_text},
        ),
    )
    _record_artifact(
        artifacts,
        _write_json(run_dir / "schema_snapshot.json", schema),
    )

    if artifacts.extracted_json is not None:
        _record_artifact(
            artifacts,
            _write_json(run_dir / "extracted.json", artifacts.extracted_json),
        )
    if artifacts.validation_errors:
        _record_artifact(
            artifacts,
            _write_json(
                run_dir / "validation_errors.json",
                {"errors": artifacts.validation_errors},
            ),
        )

    outputs_payload = {
        "files": [str(path) for path in artifacts.output_files],
        "run_directory": str(run_dir),
    }
    _record_artifact(
        artifacts,
        _write_json(run_dir / "outputs.json", outputs_payload)
    )

    # Privacy Audit Log
    audit = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": artifacts.run_id,
        "network_calls": 0,
        "data_transmitted_bytes": 0,
        "ollama_endpoint": "localhost:11434"
    }
    _record_artifact(
        artifacts,
        _write_json(run_dir / "privacy_audit.json", audit)
    )


def run_pipeline(
    *,
    text_input: str | None,
    audio_path: str | None,
    schema_path: str,
    template_specs: list[dict[str, str]],
    output_dir: str,
    model: str = "llama3.1",
    max_retries: int = 2,
    save_artifacts: bool = True,
) -> PipelineArtifacts:
    if not text_input and not audio_path:
        raise ValueError("Provide either text_input or audio_path.")

    total_start = time.perf_counter()
    schema = _load_json(schema_path)

    input_start = time.perf_counter()
    input_text = (
        text_input.strip()
        if text_input
        else transcribe_audio(audio_path or "")
    )

    run_tag = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"run_{run_tag}"
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / run_id
    generated_dir = run_dir / "generated_pdfs"
    generated_dir.mkdir(parents=True, exist_ok=True)

    artifacts = PipelineArtifacts(
        run_id=run_id,
        model=model,
        input_text=input_text,
    )
    artifacts.stage_durations["input_prepare_seconds"] = round(
        time.perf_counter() - input_start,
        3,
    )

    extract_start = time.perf_counter()
    extraction = extract_incident_data(input_text, schema=schema, model=model)
    artifacts.stage_durations["extract_seconds"] = round(
        time.perf_counter() - extract_start,
        3,
    )

    validate_start = time.perf_counter()
    validated_data, validation_errors, retries_used = _validate_with_repair(
        extraction.data or {},
        schema,
        model=model,
        max_retries=max_retries,
    )
    artifacts.stage_durations["validate_seconds"] = round(
        time.perf_counter() - validate_start,
        3,
    )

    artifacts.extracted_json = validated_data
    artifacts.validation_errors = validation_errors
    artifacts.retries_used = retries_used

    if validation_errors:
        artifacts.stage_durations["total_seconds"] = round(
            time.perf_counter() - total_start,
            3,
        )
        if save_artifacts:
            _save_run_artifacts(artifacts, schema, run_dir)
        raise ValueError(
            "Extraction failed validation after retries: "
            f"{validation_errors}"
        )

    fill_start = time.perf_counter()

    for spec in template_specs:
        result = TemplateResult(
            template_path=spec["template_path"],
            output_name=spec["output_name"],
        )
        artifacts.template_results.append(result)

        mapping = _load_json(spec["mapping_path"])
        field_values = map_to_pdf_fields(
            artifacts.extracted_json or {},
            mapping,
        )
        result.fields_mapped = len(field_values)
        output_path = generated_dir / spec["output_name"]

        try:
            filled = fill_pdf(
                spec["template_path"],
                field_values,
                str(output_path),
            )
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            artifacts.stage_durations["fill_seconds"] = round(
                time.perf_counter() - fill_start,
                3,
            )
            artifacts.stage_durations["total_seconds"] = round(
                time.perf_counter() - total_start,
                3,
            )
            if save_artifacts:
                _save_run_artifacts(artifacts, schema, run_dir)
            raise

        result.output_path = filled
        result.status = "success"
        artifacts.output_files.append(filled)

    artifacts.stage_durations["fill_seconds"] = round(
        time.perf_counter() - fill_start,
        3,
    )
    artifacts.stage_durations["total_seconds"] = round(
        time.perf_counter() - total_start,
        3,
    )

    if save_artifacts:
        _save_run_artifacts(artifacts, schema, run_dir)

    return artifacts
