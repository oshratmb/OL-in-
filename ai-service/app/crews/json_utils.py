import json


def parse_json_output(raw: str) -> dict:
    """Strips optional markdown code fences an LLM sometimes wraps JSON in."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
