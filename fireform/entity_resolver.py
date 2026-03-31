from typing import Any

UNIT_REGISTRY = {
    "engine 3": "E-3", "eng3": "E-3", "engine-3": "E-3",
    "ladder 7": "L-7", "truck 7": "L-7", "ladder-7": "L-7",
}

def normalize_units(data: dict[str, Any]) -> dict[str, Any]:
    units = data.get("nc:SystemUnit", [])
    if isinstance(units, list):
        data["nc:SystemUnit"] = [UNIT_REGISTRY.get(u.lower(), u) for u in units]
    return data
