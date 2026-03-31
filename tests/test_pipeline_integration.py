from __future__ import annotations

import json
from pathlib import Path

from fireform.pipeline import run_pipeline

def test_pipeline_runs_with_repair_cycle(tmp_path, mocker):
    schema = json.loads(
        Path("schemas/incident_schema.json").read_text(encoding="utf-8")
    )

    mocker.patch(
        "fireform.pipeline.fill_pdf",
        side_effect=lambda _t, _f, out: Path(out),
    )
    mocker.patch(
        "fireform.pipeline._load_json",
        return_value={"mock_field": "nc:IncidentID"}
    )
    mocker.patch(
        "fireform.pipeline.extract_incident_data",
        return_value=type("Obj", (), {"data": {"nc:IncidentID": "bad"}, "error": None})(),
    )
    mocker.patch(
        "fireform.pipeline.repair_extracted_data",
        return_value=type(
            "Obj",
            (),
            {
                "data": {
                    "nc:IncidentID": "FF-2026-031",
                    "nc:ActivityDate": "2026-03-31",
                    "nc:ActivityTime": "02:00:00",
                    "nc:Location": {
                        "nc:Address": "45 Park Street",
                        "nc:City": "Springfield",
                        "nc:State": "NY"
                    },
                    "em:IncidentCategoryCode": "Fire",
                    "em:UnitsDispatched": ["E1"],
                    "nc:Casualties": {
                        "nc:Injuries": 0,
                        "nc:Fatalities": 0
                    },
                    "em:PropertyDamageSeverity": "minor",
                    "nc:Narrative": "Kitchen fire was contained in 20 minutes."
                },
                "error": None
            },
        )(),
    )

    specs = [
        {
            "template_path": "templates/fire_report_template.pdf",
            "mapping_path": "dummy/path1.json",
            "output_name": "fire_report.pdf",
        },
        {
            "template_path": "templates/ems_report_template.pdf",
            "mapping_path": "dummy/path2.json",
            "output_name": "ems_report.pdf",
        },
    ]

    artifacts = run_pipeline(
        text_input="Structure fire",
        audio_path=None,
        schema_path="schemas/incident_schema.json",
        template_specs=specs,
        output_dir=str(tmp_path),
        model="mistral",
        max_retries=2,
        save_artifacts=True,
    )

    assert artifacts.extracted_json is not None
    assert artifacts.run_id.startswith("run_")
    assert artifacts.model == "mistral"
    assert artifacts.retries_used == 1
    assert "total_seconds" in artifacts.stage_durations
    assert len(artifacts.template_results) == 2
    assert all(item.status == "success" for item in artifacts.template_results)
    assert len(artifacts.output_files) == 2
    assert all("run_" in str(path) for path in artifacts.output_files)
    assert len(artifacts.artifact_files) >= 4
    assert any(
        path.name == "run_metadata.json"
        for path in artifacts.artifact_files
    )
    assert schema["type"] == "object"
