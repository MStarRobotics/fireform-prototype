from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass(slots=True)
class ExtractionResult:
    data: dict[str, Any] | None = None
    attempts: int = 1
    raw_response: str = ""
    error: str | None = None

@dataclass(slots=True)
class TemplateResult:
    template_path: str
    output_name: str
    output_path: Path | None = None
    fields_mapped: int = 0
    status: str = "pending"
    error: str | None = None

@dataclass(slots=True)
class PipelineArtifacts:
    run_id: str
    model: str
    input_text: str
    extracted_json: dict[str, Any] | None = None
    validation_errors: list[str] = field(default_factory=list)
    retries_used: int = 0
    stage_durations: dict[str, float] = field(default_factory=dict)
    template_results: list[TemplateResult] = field(default_factory=list)
    output_files: list[Path] = field(default_factory=list)
    artifact_files: list[Path] = field(default_factory=list)
