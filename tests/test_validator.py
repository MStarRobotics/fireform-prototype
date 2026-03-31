from __future__ import annotations

import json
from pathlib import Path

from fireform.validator import validate_incident_data

schema_dict = json.loads(Path("schemas/incident_schema.json").read_text(encoding="utf-8"))

def test_validate_incident_data_success():
    valid_data = {
        "nc:IncidentID": "FF-2026-001",
        "nc:ActivityDate": "2026-03-31",
        "nc:ActivityTime": "14:30:00",
        "nc:Location": {
            "nc:Address": "123 Main St",
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
        "nc:Narrative": "Responded to small kitchen fire."
    }
    
    ok, errors = validate_incident_data(valid_data, schema_dict)
    
    assert ok is True
    assert len(errors) == 0

def test_validate_incident_data_missing_required():
    invalid_data = {
        "nc:ActivityDate": "2026-03-31",
        "nc:Location": {
            "nc:Address": "123 Main St"
        }
    }
    
    ok, errors = validate_incident_data(invalid_data, schema_dict)
    
    assert ok is False
    assert len(errors) > 0
    assert any("nc:IncidentID" in err for err in errors)
