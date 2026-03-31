from __future__ import annotations

import pytest

from fireform.extractor import extract_incident_data

@pytest.fixture
def mock_ollama_chat_success(mocker):
    # Match the new NIEM schema structure
    mock_response = {
        "message": {
            "content": """
            {
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
            """
        }
    }
    return mocker.patch("ollama.chat", return_value=mock_response)


@pytest.fixture
def mock_ollama_chat_invalid_json(mocker):
    mock_response = {
        "message": {
            "content": "This is not json."
        }
    }
    return mocker.patch("ollama.chat", return_value=mock_response)


def test_extract_incident_data_success(mock_ollama_chat_success):
    result = extract_incident_data("Kitchen fire at 123 Main St.", model="mistral")
    
    assert result.data is not None
    assert result.data["nc:IncidentID"] == "FF-2026-001"
    assert "E1" in result.data["em:UnitsDispatched"]
    assert result.error is None
    # Verify we are requesting JSON format
    mock_ollama_chat_success.assert_called_once()
    call_kwargs = mock_ollama_chat_success.call_args.kwargs
    assert call_kwargs.get("format") == "json"


def test_extract_incident_data_invalid_json(mock_ollama_chat_invalid_json):
    result = extract_incident_data("Some text", model="mistral")
    
    assert result.data is None
    assert result.error is not None
    assert "Failed to parse JSON" in result.error
