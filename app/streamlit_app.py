from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from fireform.pipeline import run_pipeline

st.set_page_config(
    page_title="FireForm Prototype",
    page_icon="🔥",
    layout="wide",
)
st.title("FireForm: Report Once, File Everywhere")
st.caption(
    "Local pipeline demo: text/voice -> JSON extraction -> "
    "validation -> multi-agency PDF fill"
)

default_sample = ""
sample_path = Path("samples/sample_incident.txt")
if sample_path.exists():
    default_sample = sample_path.read_text(encoding="utf-8")

text_input = st.text_area(
    "Incident narrative",
    value=default_sample,
    height=180,
)
audio_path = st.text_input("Audio path (optional)", value="")
model_name = st.text_input("Ollama model", value="llama3.1")
max_retries = st.slider(
    "Max repair retries",
    min_value=0,
    max_value=5,
    value=2,
)
save_artifacts = st.checkbox("Save run artifacts", value=True)
run_button = st.button("Run Pipeline", type="primary")

if run_button:
    template_specs = [
        {
            "template_path": "templates/fire_report_template.pdf",
            "mapping_path": "agencies/fema_ics214/field_mapping.json" if Path("agencies/fema_ics214/field_mapping.json").exists() else "schemas/template_maps/fire_department.json",
            "output_name": "fire_department_report.pdf",
        },
        {
            "template_path": "templates/ems_report_template.pdf",
            "mapping_path": "agencies/ems_report/field_mapping.json" if Path("agencies/ems_report/field_mapping.json").exists() else "schemas/template_maps/ems_department.json",
            "output_name": "ems_department_report.pdf",
        },
    ]

    try:
        artifacts = run_pipeline(
            text_input=text_input if text_input.strip() else None,
            audio_path=audio_path.strip() or None,
            schema_path="schemas/incident_schema.json",
            template_specs=template_specs,
            output_dir="outputs",
            model=model_name.strip() or "llama3.1",
            max_retries=max_retries,
            save_artifacts=save_artifacts,
        )

        st.success("Pipeline complete")

        left, mid, right = st.columns(3)
        left.metric("Run ID", artifacts.run_id)
        mid.metric("Retries Used", str(artifacts.retries_used))
        right.metric(
            "Total Seconds",
            f"{artifacts.stage_durations.get('total_seconds', 0.0):.3f}",
        )

        if artifacts.stage_durations:
            st.subheader("Stage Durations (seconds)")
            st.json(artifacts.stage_durations)

        st.subheader("Extracted JSON")
        st.code(
            json.dumps(artifacts.extracted_json, indent=2),
            language="json",
        )

        if artifacts.template_results:
            st.subheader("Template Results")
            table_rows = [
                {
                    "template": item.template_path,
                    "output": item.output_name,
                    "status": item.status,
                    "fields_mapped": item.fields_mapped,
                    "error": item.error,
                }
                for item in artifacts.template_results
            ]
            st.dataframe(table_rows, use_container_width=True)

        st.subheader("Generated files")
        for index, file_path in enumerate(artifacts.output_files):
            path = Path(file_path)
            st.write(str(path))
            if path.exists():
                st.download_button(
                    label=f"Download {path.name}",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/pdf",
                    key=f"pdf-download-{index}",
                )

        if artifacts.artifact_files:
            st.subheader("Run Artifacts")
            for index, artifact_path in enumerate(artifacts.artifact_files):
                path = Path(artifact_path)
                st.write(str(path))
                if path.exists():
                    st.download_button(
                        label=f"Download {path.name}",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/json",
                        key=f"artifact-download-{index}",
                    )
    except Exception as exc:
        st.error(f"Pipeline failed: {exc}")
