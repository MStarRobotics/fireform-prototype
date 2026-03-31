INCIDENTS = [
    {
        "input": "Structure fire at 45 Park St, 2am, Engine 3 and Ladder 7 responded.",
        "expected": {
            "em:IncidentCategoryCode": "STRUCTURE_FIRE",
            "nc:Location": {"nc:Address": "45 Park St"},
            "nc:ActivityTime": "02:00"
        }
    },
    {
        "input": "Medical call at 100 Main St, 15:30. 1 casualty reported. Patient transported to hosp.",
        "expected": {
            "em:IncidentCategoryCode": "MEDICAL",
            "nc:Location": {"nc:Address": "100 Main St"},
            "nc:Casualties": {"nc:Injuries": 1}
        }
    },
    {
        "input": "Hazmat spill on Highway 9 at 8am. Engine 1 on scene.",
        "expected": {
            "em:IncidentCategoryCode": "HAZMAT",
            "nc:Location": {"nc:Address": "Highway 9"},
            "nc:ActivityTime": "08:00"
        }
    }
]
